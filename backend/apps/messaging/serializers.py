from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.serializers import UserBriefSerializer
from apps.messaging.models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_details = UserBriefSerializer(source="sender", read_only=True)
    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "sender_details", "content", "created_at", "updated_at", "is_read", "read_at", "is_deleted"]
        read_only_fields = ["sender", "conversation", "created_at", "updated_at", "is_read", "read_at", "is_deleted"]
    def validate_content(self, value):
        if not value.strip(): raise serializers.ValidationError("A message cannot be empty.")
        return value.strip()

class ConversationSerializer(serializers.ModelSerializer):
    participants_details = UserBriefSerializer(source="participants", many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    class Meta:
        model = Conversation
        fields = ["id", "participants", "participants_details", "created_at", "updated_at", "last_message", "unread_count"]
        read_only_fields = ["created_at", "updated_at"]
    def get_last_message(self, obj):
        item = obj.messages.filter(is_deleted=False).order_by("-created_at").first()
        return MessageSerializer(item).data if item else None
    def get_unread_count(self, obj):
        user = self.context["request"].user
        return obj.messages.filter(is_read=False, is_deleted=False).exclude(sender=user).count()
    def validate_participants(self, users):
        request = self.context["request"]
        users = list(users)
        if request.user not in users: users.append(request.user)
        if len(users) != 2: raise serializers.ValidationError("Direct conversations require exactly one other participant.")
        if any(user.is_patient_account for user in users): raise serializers.ValidationError("Patient accounts cannot use internal messaging.")
        return users
    def create(self, validated_data):
        users = validated_data.pop("participants")
        existing = Conversation.objects.filter(participants=users[0]).filter(participants=users[1])
        for conversation in existing:
            if conversation.participants.count() == 2: return conversation
        conversation = Conversation.objects.create(); conversation.participants.set(users); return conversation
