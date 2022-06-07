import uuid

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UserManager(BaseUserManager):
    """
    User Manager to create custom user.
    """

    use_in_migrations = True

    def _create_user(self, email, **extra_fields):
        """Create and save a user with the given email, and password."""
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save()
        return user

    def create_user(self, email, username, **extra_fields):
        if not email:
            raise ValueError("User must have an email")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.save()
        return user

    def create_superuser(self, email, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_admin", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Staff user must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Super user must have is_superuser=True")
        if extra_fields.get("is_admin") is not True:
            raise ValueError("Super user must have is_admin=True")
        print("SUPERUSER")
        print(extra_fields)
        return self._create_user(email, **extra_fields)


class UserRole(models.Model):
    """
    User Role
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    role_name = models.CharField(max_length=255)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model
    """

    id = models.UUIDField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    # username = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, null=True)
    is_active = models.BooleanField(default=False, null=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=50)
    role = models.ForeignKey(UserRole, max_length=255, on_delete=models.PROTECT)
    profile_picture = models.CharField(max_length=500)
    status = models.CharField(max_length=50)
    subscription = models.CharField(max_length=50)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def get_full_name(self):
        """
        Helper Functions
        """
        return f"{self.first_name} - {self.last_name}"

    # def get_username(self):
    #     return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def __str__(self):
        """
        Helper Functions
        """
        return str(self.email)
