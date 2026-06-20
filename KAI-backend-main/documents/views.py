from rest_framework import views, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse
import os

from .models import SharedDocument, DocumentRequest
from .serializers import (
    SharedDocumentSerializer, SendDocumentSerializer,
    DocumentRequestSerializer, CreateDocumentRequestSerializer,
)
from .services import send_document, create_document_request, decline_document_request


class SendDocumentView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ser = SendDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        if d['file'].size > settings.MAX_ATTACHMENT_SIZE:
            return Response({'file': ['File too large.']}, status=400)

        if str(d['recipient_id']) == str(request.user.id):
            return Response({'recipient_id': ['Cannot send to yourself.']}, status=400)

        doc = send_document(
            sender=request.user,
            recipient_id=d['recipient_id'],
            file=d['file'],
            message=d.get('message', ''),
            fulfills_request_id=d.get('fulfills_request_id'),
            request=request,
        )
        return Response(
            SharedDocumentSerializer(doc, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class InboxView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SharedDocumentSerializer

    def get_queryset(self):
        return (SharedDocument.objects
                .filter(recipient=self.request.user)
                .select_related('sender', 'recipient', 'fulfills_request'))


class SentView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SharedDocumentSerializer

    def get_queryset(self):
        return (SharedDocument.objects
                .filter(sender=self.request.user)
                .select_related('sender', 'recipient', 'fulfills_request'))


class DocumentDownloadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        doc = get_object_or_404(SharedDocument, id=pk)
        if doc.recipient_id != request.user.id and doc.sender_id != request.user.id:
            return Response({'detail': 'Not allowed.'}, status=403)
        if doc.recipient_id == request.user.id and not doc.is_downloaded:
            doc.is_downloaded = True
            doc.save(update_fields=['is_downloaded'])
        response = FileResponse(doc.file.open('rb'), content_type=doc.content_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{doc.filename}"'
        return response


class DocumentRequestListCreateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        direction = request.query_params.get('direction', 'all')
        if direction == 'incoming':
            qs = DocumentRequest.objects.filter(target=request.user)
        elif direction == 'outgoing':
            qs = DocumentRequest.objects.filter(requester=request.user)
        else:
            from django.db.models import Q
            qs = DocumentRequest.objects.filter(
                Q(requester=request.user) | Q(target=request.user)
            )
        qs = qs.select_related('requester', 'target', 'fulfilled_document__sender', 'fulfilled_document__recipient')
        ser = DocumentRequestSerializer(qs, many=True, context={'request': request})
        return Response(ser.data)

    def post(self, request):
        ser = CreateDocumentRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        if str(d['target_id']) == str(request.user.id):
            return Response({'target_id': ['Cannot request from yourself.']}, status=400)

        req = create_document_request(
            requester=request.user,
            target_id=d['target_id'],
            document_type=d['document_type'],
            message=d.get('message', ''),
            request=request,
        )
        return Response(
            DocumentRequestSerializer(req, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentRequestActionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        req = get_object_or_404(DocumentRequest, id=pk)
        action = request.data.get('action')

        if action == 'decline':
            if req.target_id != request.user.id:
                return Response({'detail': 'Only the target can decline.'}, status=403)
            if req.status != 'pending':
                return Response({'detail': f'Request is already {req.status}.'}, status=400)
            req = decline_document_request(req=req, actor=request.user, request=request)
            return Response(DocumentRequestSerializer(req, context={'request': request}).data)

        return Response({'detail': 'Invalid action.'}, status=400)
