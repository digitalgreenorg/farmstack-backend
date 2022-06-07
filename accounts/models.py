import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
from datahub.base_models import TimeStampMixin

class UserManager(BaseUserManager):
    """ UserManager to manage creation of users """
    use_in_migrations = True

    def _create_user(self, email, **extra_fields):
        """ Save an admin or super user """
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save()
        return user

    def create_user(self, email, **extra_fields):
        """ Save a user with the given email and other fields """
        if not email:
            raise ValueError("User must have an email")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save()
        return user

    def create_superuser(self, email, **extra_fields):
        """ Save an admin or super user with role_id set to admin datahub user """
        extra_fields.setdefault('status', True)
        # extra_fields.setdefault('role', "f1b55b3e-c5c7-453d-87e6-0e388c9d1fc3")
        extra_fields.setdefault('role_id', int(1))
        return self._create_user(email, **extra_fields)


class UserRole(models.Model):
    """ UserRole model for user roles of the datahub users """
    ROLES = (
            ('datahub_admin', 'datahub_admin'),
            ('datahub_team_member', 'datahub_team_member'),
            ('datahub_guest_user', 'datahub_guest_user'),
            ('datahub_participant_root', 'datahub_participant_root'),
            ('datahub_participant_team', 'datahub_participant_team')
            )

    # id = models.UUIDField(
    #         primary_key=True,
    #         default=uuid.uuid4,
    #         editable=False)
    id = models.IntegerField(primary_key=True)
    role_name = models.CharField(max_length=255, null=True, blank=True,
            choices=ROLES)


class User(AbstractBaseUser, TimeStampMixin):
    """ User model for of all the datahub users """
    id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False)
    password = None
    last_login = None
    is_superuser = None
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, null=True)
    phone_number = models.CharField(max_length=50)
    role = models.ForeignKey(UserRole, max_length=255, on_delete=models.PROTECT)
    profile_picture = models.CharField(max_length=500)
    status = models.BooleanField(default=False, null=True)
    subscription = models.CharField(max_length=50)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def get_full_name(self):
        return f"{self.first_name} - {self.last_name}"

    def __str__(self):
        return self.email
