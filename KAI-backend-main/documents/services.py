from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from core.services import write_audit
from notifications.services import notify
from .models import SharedDocument, DocumentRequest

User = get_user_model()


def send_document(*, sender, recipient_id, file, message='', fulfills_request_id=None, request=None):
    recipient = User.objects.get(id=recipient_id)
    with transaction.atomic():
        doc = SharedDocument.objects.create(
            sender=sender,
            recipient=recipient,
            file=file,
            filename=file.name,
            size=file.size,
            content_type=getattr(file, 'content_type', ''),
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
                    link='/documents',
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
            body=f"{file.name}" + (f" — {message}" if message else ""),
            link='/documents',
            actor=sender,
        )
    return doc


def create_document_request(*, requester, target_id, document_type, message='', request=None):
    target = User.objects.get(id=target_id)
    with transaction.atomic():
        req = DocumentRequest.objects.create(
            requester=requester,
            target=target,
            document_type=document_type,
            message=message,
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
            link='/documents',
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
            link='/documents',
            actor=actor,
        )
    return req
