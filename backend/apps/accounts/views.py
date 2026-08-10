from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    LoginResponseSerializer,
    RegisterPatientSerializer,
    ResetPasswordSerializer,
    UserSerializer,
)
from apps.core.models import AuditLog
from apps.core.services import audit_log


def _get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@extend_schema(
    request=CustomTokenObtainPairSerializer,
    responses=LoginResponseSerializer,
    tags=["auth"],
)
class LoginView(APIView):
    """Authenticate a user, return JWT pair, and enforce lockout after failed attempts."""

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response(
                {"detail": "Please provide both username and password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(username=username).first()
        if user:
            if user.locked_until and user.locked_until > timezone.now():
                minutes = int((user.locked_until - timezone.now()).total_seconds() // 60) + 1
                return Response(
                    {"detail": f"Account temporarily locked. Try again in {minutes} minute(s)."},
                    status=status.HTTP_423_LOCKED,
                )
            if not user.is_active:
                return Response(
                    {"detail": "This account is deactivated. Contact your administrator."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        auth_user = authenticate(request, username=username, password=password)
        if auth_user is None:
            candidate = User.objects.filter(username=username).first()
            if candidate:
                candidate.failed_login_attempts += 1
                if candidate.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    candidate.locked_until = timezone.now() + timezone.timedelta(
                        minutes=settings.LOCKOUT_MINUTES
                    )
                    candidate.failed_login_attempts = 0
                candidate.save(update_fields=["failed_login_attempts", "locked_until"])
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        auth_user.failed_login_attempts = 0
        auth_user.locked_until = None
        auth_user.last_login_ip = _get_client_ip(request)
        auth_user.save(update_fields=["failed_login_attempts", "locked_until", "last_login_ip"])

        token = CustomTokenObtainPairSerializer.get_token(auth_user)
        audit_log(auth_user, AuditLog.ACTION_LOGIN, "auth", record=auth_user.username, request=request)

        return Response(
            {
                "access": str(token.access_token),
                "refresh": str(token),
                "user": UserSerializer(auth_user).data,
            }
        )


class RefreshView(APIView):
    permission_classes = [AllowAny]
    tags = ["auth"]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            refresh = RefreshToken(refresh_token)
            return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
        except Exception:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    tags = ["auth"]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                RefreshToken(refresh_token).blacklist()
        except Exception:
            pass
        audit_log(request.user, AuditLog.ACTION_LOGOUT, "auth", record=request.user.username, request=request)
        return Response({"detail": "Successfully logged out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    tags = ["auth"]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ForgotPasswordView(APIView):
    """Send a password-reset email containing a secure, time-limited link."""

    permission_classes = [AllowAny]
    tags = ["auth"]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            try:
                send_mail(
                    subject="Reset your Hospital Management System password",
                    message=f"Hi {user.get_full_name() or user.username},\n\n"
                            f"Click the link below to reset your password:\n{link}\n\n"
                            f"This link expires in 24 hours. If you did not request this, "
                            f"you can safely ignore this email.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception:
                pass
        # Always return success to avoid leaking which emails exist.
        return Response({"detail": "If an account exists for that email, a reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    tags = ["auth"]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid_param = request.data.get("uid")
        try:
            user_id = urlsafe_base64_decode(uid_param or "")
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "This reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = serializer.validated_data["token"]
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "This reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["password"])
        user.save()
        audit_log(user, AuditLog.ACTION_UPDATE, "auth", record=f"password reset {user.username}")
        return Response({"detail": "Your password has been reset. You can now sign in."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    tags = ["auth"]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"detail": "Your current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        audit_log(user, AuditLog.ACTION_UPDATE, "auth", record=f"password changed {user.username}", request=request)
        return Response({"detail": "Password changed successfully. Please sign in again."})


class RegisterView(generics.CreateAPIView):
    """Self-registration for patients."""

    permission_classes = [AllowAny]
    serializer_class = RegisterPatientSerializer
    tags = ["auth"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"detail": "Account created successfully. You can now sign in.", "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )
