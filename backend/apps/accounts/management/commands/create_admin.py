from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from getpass import getpass


class Command(BaseCommand):
    help = "Create a new Hospital Management System administrator."

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Hospital Management System - Create Admin ===\n"
            )
        )

        # Username
        username = input("Username: ").strip()

        if not username:
            raise CommandError("Username cannot be empty.")

        if User.objects.filter(username=username).exists():
            raise CommandError(
                f"An account with username '{username}' already exists."
            )

        # Email
        email = input("Email: ").strip()

        if not email:
            raise CommandError("Email cannot be empty.")

        if User.objects.filter(email=email).exists():
            raise CommandError(
                f"An account with email '{email}' already exists."
            )

        # Password
        password = getpass("Password: ")
        password_confirm = getpass("Confirm password: ")

        if not password:
            raise CommandError("Password cannot be empty.")

        if password != password_confirm:
            raise CommandError("Passwords do not match.")

        if len(password) < 8:
            raise CommandError(
                "Password must contain at least 8 characters."
            )

        # Create admin
        try:
            admin = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )

            admin.is_staff = True
            admin.is_superuser = True
            admin.is_active = True

            admin.save()

        except Exception as exc:
            raise CommandError(
                f"Failed to create administrator: {exc}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "✓ Administrator account created successfully!"
            )
        )
        self.stdout.write("")
        self.stdout.write(f"Username: {username}")
        self.stdout.write(f"Email: {email}")
        self.stdout.write("Admin privileges: Enabled")
        self.stdout.write("")