import uuid

# from utils.validators import validate_file_size
from core.base_models import TimeStampMixin
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from utils.validators import validate_file_size


class UserManager(BaseUserManager):
    """UserManager to manage creation of users"""

    use_in_migrations = True

    def _create_user(self, email, **extra_fields):
        """Save an admin or super user"""
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save()
        return user

    def create_superuser(self, email, **extra_fields):
        """Save an admin or super user with role_id set to admin datahub user"""
        extra_fields.setdefault("status", False)
        extra_fields.setdefault("role_id", int(1))
        return self._create_user(email, **extra_fields)


class UserRole(models.Model):
    """UserRole model for user roles of the datahub users
    User role mapping with id:
        ADMIN: 1
        TEAM MEMBER: 2
        PARTICIPANT ROOT: 3
        PARTICIPANT TEAM MEMBER: 4
        GUEST: 5
    """

    ROLES = (
        ("ADMIN", "ADMIN"),
        ("PARTICIPANT ROOT", "PARTICIPANT ROOT"),
        ("PARTICIPANT TEAM MEMBER", "PARTICIPANT TEAM MEMBER"),
        ("TEAM MEMBER", "TEAM MEMBER"),
        ("GUEST", "GUEST"),
    )

    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id = models.IntegerField(primary_key=True)
    role_name = models.CharField(max_length=255, null=True, blank=True, choices=ROLES)

    def __str__(self):
        return self.role_name


def auto_str(cls):
    def __str__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join("%s=%s" % item for item in vars(self).items()),
        )

    cls.__str__ = __str__
    return cls


@auto_str
class User(AbstractBaseUser, TimeStampMixin):
    """User model of all the datahub users

    status:
        true (active) = 1
        false (inactive) = 0
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    password = None
    last_login = None
    is_superuser = None
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    role = models.ForeignKey(
        UserRole,
        max_length=255,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    profile_picture = models.FileField(
        upload_to=settings.PROFILE_PICTURES_URL,
        null=True,
        blank=True,
        validators=[validate_file_size],
    )
    status = models.BooleanField(default=True)
    subscription = models.CharField(max_length=50, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"

    def get_full_name(self):
        """
        Helper Functions
        """
        return f"{self.first_name} - {self.last_name}"

    def __str__(self):
        return self.email
