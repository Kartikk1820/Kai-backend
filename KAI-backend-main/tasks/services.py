"""Tasks service layer: guarded FSM transitions, ordering, links. All status
changes funnel through here so the board can never reach an illegal state."""
from django.db import transaction
from django_fsm import TransitionNotAllowed, can_proceed
from rest_framework.exceptions import ValidationError, PermissionDenied

from core.services import write_audit
from core.permissions_catalog import TASK_TRANSITION_ANY, TASK_MANAGE, TASK_APPROVE, TASK_BLOCK, TASK_REOPEN
from .models import Task, Comment, TaskLink


# action -> (fsm method name, target status)
ACTIONS = {
    'start': ('start', 'in_progress'),
    'submit_for_review': ('submit_for_review', 'review'),
    'approve': ('approve', 'done'),
    'send_back': ('send_back', 'in_progress'),
    'block': ('block', 'blocked'),
    'unblock': ('unblock', 'todo'),
    'reopen': ('reopen', 'review'),
}

FORCE = {
    'todo': 'force_todo',
    'in_progress': 'force_in_progress',
    'review': 'force_review',
    'blocked': 'force_blocked',
    'done': 'force_done',
}


def _can_edit(user, task):
    if user.user_type == 'Admin' or user.has_perm_key(TASK_TRANSITION_ANY):
        return True
    if task.reporter_id == user.id or task.assignee_id == user.id or task.created_by_id == user.id:
        return True
    # Manager of the assignee
    if task.assignee and task.assignee.manager_id == user.id:
        return True
    return False


class TaskService:

    @classmethod
    @transaction.atomic
    def transition(cls, task_id, user, action=None, target=None, reason=None, request=None):
        task = Task.objects.select_for_update().get(id=task_id)
        old = task.status
        is_admin_override = user.user_type == 'Admin' or user.has_perm_key(TASK_TRANSITION_ANY)

        # Permission to touch this task at all
        if not _can_edit(user, task):
            raise PermissionDenied("You do not have permission to move this task.")

        # Blocking requires a reason
        if (action == 'block' or target == 'blocked') and not (reason and reason.strip()):
            raise ValidationError({'reason': 'A reason is required to block a task.'})

        # Resolve the FSM method
        if action and action in ACTIONS:
            method_name, _target = ACTIONS[action]
        elif target and is_admin_override:
            if target == old:
                return task
            method_name = FORCE[target]
        elif target and target in FORCE:
            # Non-admin used a raw target (e.g. drag): map to a legal action if possible
            method_name = cls._target_to_action(old, target)
            if method_name is None:
                raise ValidationError(
                    {'detail': f"Moving from {old} to {target} is not allowed."}
                )
        else:
            raise ValidationError({'action': 'Unknown action.'})

        if not is_admin_override:
            if method_name == 'approve' and not user.has_perm_key(TASK_APPROVE):
                raise PermissionDenied("You do not have permission to approve tasks.")
            if method_name == 'block' and not user.has_perm_key(TASK_BLOCK):
                raise PermissionDenied("You do not have permission to block tasks.")
            if method_name == 'reopen' and not user.has_perm_key(TASK_REOPEN):
                raise PermissionDenied("You do not have permission to reopen tasks.")

        method = getattr(task, method_name)
        if not can_proceed(method):
            raise ValidationError({'detail': f"Transition from {old} is not permitted."})
        try:
            method()
        except TransitionNotAllowed:
            raise ValidationError({'detail': f"Transition from {old} is not permitted."})

        task.save()

        if reason:
            Comment.objects.create(task=task, author=user, body=f"[Blocked] {reason}")

        write_audit(
            actor=user, model_name='Task', object_id=task.id, action='transition',
            old_state=old, new_state=task.status, request=request,
            context={'override': is_admin_override and bool(target)},
        )

        # Notify assignee on completion / reassignment-relevant moves (kept light)
        return task

    @staticmethod
    def _target_to_action(old, target):
        legal = {
            ('todo', 'in_progress'): 'start',
            ('in_progress', 'review'): 'submit_for_review',
            ('review', 'done'): 'approve',
            ('review', 'in_progress'): 'send_back',
            ('todo', 'blocked'): 'block',
            ('in_progress', 'blocked'): 'block',
            ('review', 'blocked'): 'block',
            ('blocked', 'todo'): 'unblock',
            ('done', 'review'): 'reopen',
        }
        return legal.get((old, target))

    @classmethod
    @transaction.atomic
    def reorder(cls, task_id, user, before_id=None, after_id=None, status=None):
        task = Task.objects.select_for_update().get(id=task_id)
        if status and status != task.status:
            # reorder shouldn't change status; ignore mismatches
            pass
        siblings = list(
            Task.objects.filter(status=task.status).exclude(id=task.id).order_by('position', 'created_at')
        )
        new_pos = cls._position_between(siblings, before_id, after_id)
        task.position = new_pos
        task.save(update_fields=['position', 'updated_at'])
        return task

    @staticmethod
    def _position_between(siblings, before_id, after_id):
        pos_by_id = {t.id: t.position for t in siblings}
        if before_id and before_id in pos_by_id:
            ref = pos_by_id[before_id]
            below = [p for p in pos_by_id.values() if p < ref]
            lower = max(below) if below else ref - 1
            return (lower + ref) / 2
        if after_id and after_id in pos_by_id:
            ref = pos_by_id[after_id]
            above = [p for p in pos_by_id.values() if p > ref]
            upper = min(above) if above else ref + 1
            return (ref + upper) / 2
        # default: top of column
        top = min(pos_by_id.values()) if pos_by_id else 0
        return top - 1

    @classmethod
    @transaction.atomic
    def add_link(cls, task, user, relation, target_task_id, request=None):
        if target_task_id == task.id:
            raise ValidationError({'target_task_id': 'A task cannot link to itself.'})
        target = Task.objects.get(id=target_task_id)
        TaskLink.objects.get_or_create(source_task=task, target_task=target, relation=relation)
        # Mirror blocks <-> is_blocked_by
        mirror = {'blocks': 'is_blocked_by', 'is_blocked_by': 'blocks'}.get(relation)
        if mirror:
            TaskLink.objects.get_or_create(source_task=target, target_task=task, relation=mirror)
        elif relation == 'relates_to':
            TaskLink.objects.get_or_create(source_task=target, target_task=task, relation='relates_to')
        return task

    @classmethod
    @transaction.atomic
    def delete(cls, task, user, request=None):
        if not (user.user_type == 'Admin' or user.has_perm_key(TASK_MANAGE)
                or task.reporter_id == user.id or task.created_by_id == user.id
                or (task.assignee and task.assignee.manager_id == user.id)):
            raise PermissionDenied("You cannot delete this task.")
        tid = task.id
        write_audit(actor=user, model_name='Task', object_id=tid, action='deleted',
                    old_state=task.status, new_state='deleted', request=request)
        task.delete()
