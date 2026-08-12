from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.models import AuditLog
from apps.core.services import audit_log, notify
from apps.messaging.models import Conversation, Message
from apps.messaging.serializers import ConversationSerializer, MessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["participants__first_name", "participants__last_name", "participants__username", "messages__content"]
    def get_queryset(self): return Conversation.objects.filter(participants=self.request.user).prefetch_related("participants", "messages__sender").distinct()
    def perform_create(self, serializer): serializer.save()
    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == "GET":
            conversation.messages.filter(is_read=False, is_deleted=False).exclude(sender=request.user).update(is_read=True, read_at=timezone.now())
            page = self.paginate_queryset(conversation.messages.filter(is_deleted=False).select_related("sender"))
            serializer = MessageSerializer(page if page is not None else conversation.messages.filter(is_deleted=False), many=True)
            return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = Message.objects.create(conversation=conversation, sender=request.user, content=serializer.validated_data["content"])
        conversation.save(update_fields=["updated_at"])
        for user in conversation.participants.exclude(pk=request.user.pk): notify(user, "New message", f"{request.user.get_full_name() or request.user.username}: {message.content[:100]}", link="/messages")
        audit_log(request.user, AuditLog.ACTION_CREATE, "messages.message", record=str(message.id), object_id=message.id, request=request)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

class MessageViewSet(viewsets.GenericViewSet):
    queryset = Message.objects.select_related("conversation", "sender")
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self): return self.queryset.filter(conversation__participants=self.request.user).get(pk=self.kwargs["pk"])
    def partial_update(self, request, pk=None):
        message = self.get_object()
        if message.sender != request.user: return Response({"detail": "Only the sender can edit this message."}, status=403)
        serializer = self.get_serializer(message, data=request.data, partial=True); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data)
    def destroy(self, request, pk=None):
        message = self.get_object()
        if message.sender != request.user: return Response({"detail": "Only the sender can delete this message."}, status=403)
        message.is_deleted = True; message.content = ""; message.save(update_fields=["is_deleted", "content", "updated_at"]); return Response(status=204)
