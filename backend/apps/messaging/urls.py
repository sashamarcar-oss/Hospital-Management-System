from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.messaging.views import ConversationViewSet, MessageViewSet
router = DefaultRouter(); router.register("conversations", ConversationViewSet, basename="conversation"); router.register("", MessageViewSet, basename="message")
urlpatterns = router.urls
