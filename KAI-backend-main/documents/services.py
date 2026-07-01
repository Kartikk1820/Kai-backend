from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError
from core.services import write_audit
from notifications.services import notify
from .models import SharedDocument, DocumentRequest, DocumentSendApproval

User = get_user_model()


def send_document(*, sender, recipient_id, file=None, url=None, link_label='',
                  message='', fulfills_request_id=None, escalation_minutes=240,
                  _force_send=False, request=None):
    """
    Send a document. If recipient is a Client and sender lacks document.send_to_client
    permission, creates a DocumentSendApproval for manager review instead.
    Returns (SharedDocument | DocumentSendApproval, 'sent' | 'pending_approval').
    """
    recipient = User.objects.get(id=recipient_id)

    needs_approval = (
        not _force_send
        and recipient.user_type == 'Client'
        and not sender.has_perm_key('document.send_to_client')
    )

    if needs_approval:
        appr = _create_approval(
            sender=sender, recipient=recipient, file=file, url=url,
            link_label=link_label, message=message,
            fulfills_request_id=fulfills_request_id,
            escalation_minutes=escalation_minutes, request=request,
        )
        return appr, 'pending_approval'

    if file:
        filename = file.name
        size = file.size
        content_type = getattr(file, 'content_type', '')
    else:
        filename = link_label or url
        size = 0
        content_type = ''

    with transaction.atomic():
        doc = SharedDocument.objects.create(
            sender=sender,
            recipient=recipient,
            file=file,
            url=url,
            link_label=link_label,
            filename=filename,
            size=size,
            content_type=content_type,
            message=message,
        )
        if fulfills_request_id:
            try:
                req = DocumentRequest.objects.select_for_update().get(
                    id=fulfills_request_id, target=sender, status='pending'
                )
                req.status = 'fulfilled'
                req.save(update_fields=['status', 'updated_at'])
                doc.fulfills_request = req
                doc.save(update_fields=['fulfills_request'])
                notify(
                    user=req.requester,
                    kind='document_request_fulfilled',
                    title=f"{sender.full_name} fulfilled your document request",
                    body=f"Document: {req.document_type}",
                    link='/documents?tab=requests',
                    actor=sender,
                )
            except DocumentRequest.DoesNotExist:
                pass

        write_audit(
            actor=sender, model_name='SharedDocument', object_id=doc.id,
            action='sent', new_state=f"to:{recipient_id}", request=request,
        )
        notify(
            user=recipient,
            kind='document_received',
            title=f"{sender.full_name} sent you a document",
            body=filename + (f" — {message}" if message else ""),
            link='/documents?tab=inbox',
            actor=sender,
        )
    return doc, 'sent'


def _create_approval(*, sender, recipient, file=None, url=None, link_label='',
                     message='', fulfills_request_id=None, escalation_minutes=240,
                     request=None):
    if not sender.manager_id:
        raise ValidationError(
            "You have no manager assigned. Cannot send documents to clients without a manager."
        )

    if file:
        filename = file.name
        size = file.size
        content_type = getattr(file, 'content_type', '')
    else:
        filename = link_label or url or ''
        size = 0
        content_type = ''

    with transaction.atomic():
        appr = DocumentSendApproval.objects.create(
            sender=sender,
            recipient=recipient,
            approver_id=sender.manager_id,
            file=file,
            url=url or None,
            link_label=link_label,
            filename=filename,
            size=size,
            content_type=content_type,
            message=message,
            fulfills_request_id=fulfills_request_id,
            escalation_minutes=escalation_minutes,
        )
        write_audit(
            actor=sender, model_name='DocumentSendApproval', object_id=appr.id,
            action='created', new_state='pending', request=request,
        )
        notify(
            user=sender.manager,
            kind='document_approval_requested',
            title=f"{sender.full_name} wants to send a document to a client",
            body=f"{filename} → {recipient.full_name}",
            link='/documents?tab=approvals',
            actor=sender,
        )
        notify(
            user=sender,
            kind='document_approval_pending',
            title="Document sent for manager approval",
            body=f"{filename} — awaiting {sender.manager.full_name}'s approval",
            link='/documents?tab=sent',
            actor=sender,
        )
    return appr


def approve_document_send(*, appr, actor, request=None):
    with transaction.atomic():
        appr = DocumentSendApproval.objects.select_for_update().get(id=appr.id)
        if appr.status in ('approved', 'rejected'):
            raise ValidationError(f"Already {appr.status}.")

        recipient = User.objects.get(id=appr.recipient_id)

        shared_doc = SharedDocument(
            sender=appr.sender,
            recipient=recipient,
            url=appr.url or None,
            link_label=appr.link_label,
            filename=appr.filename,
            size=appr.size,
            content_type=appr.content_type,
            message=appr.message,
        )
        if appr.file and appr.file.name:
            shared_doc.file.name = appr.file.name  # point to same file on disk
        shared_doc.save()

        if appr.fulfills_request_id:
            try:
                req = DocumentRequest.objects.select_for_update().get(
                    id=appr.fulfills_request_id, status='pending'
                )
                req.status = 'fulfilled'
                req.save(update_fields=['status', 'updated_at'])
                shared_doc.fulfills_request = req
                shared_doc.save(update_fields=['fulfills_request'])
                notify(
                    user=req.requester,
                    kind='document_request_fulfilled',
                    title=f"{appr.sender.full_name} fulfilled your document request",
                    body=f"Document: {req.document_type}",
                    link='/documents?tab=requests',
                    actor=appr.sender,
                )
            except DocumentRequest.DoesNotExist:
                pass

        # Transfer file ownership: null approval's file ref without deleting physical file
        DocumentSendApproval.objects.filter(id=appr.id).update(
            status='approved', file='', updated_at=now(),
        )

        write_audit(
            actor=actor, model_name='DocumentSendApproval', object_id=appr.id,
            action='approved', request=request,
        )
        write_audit(
            actor=appr.sender, model_name='SharedDocument', object_id=shared_doc.id,
            action='sent', new_state=f"to:{appr.recipient_id}", request=request,
        )
        notify(
            user=appr.sender,
            kind='document_approval_approved',
            title=f"Your document was approved and delivered",
            body=f"{appr.filename} → {recipient.full_name}",
            link='/documents?tab=sent',
            actor=actor,
        )
        notify(
            user=recipient,
            kind='document_received',
            title=f"{appr.sender.full_name} sent you a document",
            body=appr.filename + (f" — {appr.message}" if appr.message else ""),
            link='/documents?tab=inbox',
            actor=appr.sender,
        )
    return shared_doc


def reject_document_send(*, appr, actor, comment='', request=None):
    with transaction.atomic():
        appr = DocumentSendApproval.objects.select_for_update().get(id=appr.id)
        if appr.status in ('approved', 'rejected'):
            raise ValidationError(f"Already {appr.status}.")

        appr.status = 'rejected'
        appr.rejection_comment = comment
        appr.save(update_fields=['status', 'rejection_comment', 'updated_at'])

        if appr.file:
            appr.file.delete(save=False)

        write_audit(
            actor=actor, model_name='DocumentSendApproval', object_id=appr.id,
            action='rejected', request=request,
        )
        notify(
            user=appr.sender,
            kind='document_approval_rejected',
            title="Your document was rejected",
            body=appr.filename + (f" — {comment}" if comment else ""),
            link='/documents?tab=sent',
            actor=actor,
        )
    return appr


def delete_document(*, doc, actor, request=None):
    if doc.sender_id != actor.id:
        raise PermissionError("Only the sender can unsend a document.")
    with transaction.atomic():
        write_audit(
            actor=actor, model_name='SharedDocument', object_id=doc.id,
            action='deleted', new_state='unsent', request=request,
        )
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()


def create_document_request(*, requester, target_id, document_type, message='',
                             attachment_file=None, attachment_url=None, attachment_link_label='',
                             request=None):
    target = User.objects.get(id=target_id)
    attachment_filename = ''
    if attachment_file:
        attachment_filename = attachment_file.name
    elif attachment_url:
        attachment_filename = attachment_link_label or attachment_url

    with transaction.atomic():
        req = DocumentRequest.objects.create(
            requester=requester,
            target=target,
            document_type=document_type,
            message=message,
            attachment_file=attachment_file,
            attachment_url=attachment_url or None,
            attachment_filename=attachment_filename,
        )
        write_audit(
            actor=requester, model_name='DocumentRequest', object_id=req.id,
            action='created', new_state='pending', request=request,
        )
        notify(
            user=target,
            kind='document_request',
            title=f"{requester.full_name} is requesting a document from you",
            body=f"Document needed: {document_type}" + (f" — {message}" if message else ""),
            link='/documents?tab=requests',
            actor=requester,
        )
    return req


def decline_document_request(*, req, actor, request=None):
    with transaction.atomic():
        req.status = 'declined'
        req.save(update_fields=['status', 'updated_at'])
        write_audit(
            actor=actor, model_name='DocumentRequest', object_id=req.id,
            action='declined', old_state='pending', new_state='declined', request=request,
        )
        notify(
            user=req.requester,
            kind='document_request_declined',
            title=f"{actor.full_name} declined your document request",
            body=f"Document: {req.document_type}",
            link='/documents?tab=requests',
            actor=actor,
        )
    return req
