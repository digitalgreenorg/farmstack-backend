import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.conf import settings

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, **extra_fields):
        """ Create and save a user with the given email, and password. """
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save()
        return user


    def create_user(self, id, email, username, **extra_fields):
        if not email:
            raise ValueError("User must have an email")
        # if not id:
        #     id = models.UUIDField()
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save()
        return user

    def create_superuser(self, email, **extra_fields):
        # extra_fields.setdefault('id', models.UUIDField(default=uuid.uuid4))
        # extra_fields.setdefault('is_active', True)
        # extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('status', True)
        extra_fields.setdefault('role', 1)


        # if extra_fields.get('is_staff') is not True:
        #     raise ValueError('Staff user must have is_staff=True')
        # if extra_fields.get('is_superuser') is not True:
        #     raise ValueError('Super user must have is_superuser=True')
        # if extra_fields.get('is_admin') is not True:
        #     raise ValueError('Super user must have is_admin=True')
        return self._create_user(email, **extra_fields)


class UserRole(models.Model):
    ROLES = (
            ('datahub_admin', 'datahub_admin'),
            ('datahub_team_member', 'datahub_team_member'),
            ('datahub_guest_user', 'datahub_guest_user'),
            ('datahub_participant_root', 'datahub_participant_root'),
            ('datahub_participant_team', 'datahub_participant_team')
            )

    id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False)
    role_name = models.CharField(max_length=255, null=True, blank=True,
            choices=ROLES)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False)
    email = models.EmailField(max_length=255, unique=True)
    # username = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, null=True)
    # is_active = models.BooleanField(default=False, null=True)
    # is_staff = models.BooleanField(default=False)
    # is_admin = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=50)
    role = models.ForeignKey(UserRole, max_length=255, on_delete=models.CASCADE)
    profile_picture = models.CharField(max_length=500)
    status = models.BooleanField(default=False, null=True)
    subscription = models.CharField(max_length=50)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def get_full_name(self):
        return f"{self.first_name} - {self.last_name}"

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def __str__(self):
        return self.email



