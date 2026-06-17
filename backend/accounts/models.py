# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from telephony_toolbox.models import UUIDTimestampedModel


class AuthSource(models.TextChoices):
    ENTRA = 'entra', 'Entra'
    LDAP = 'ldap', 'LDAP'
    OIDC = 'oidc', 'OIDC/OAuth'
    LOCAL = 'local', 'Local'


class UserRole(models.TextChoices):
    STANDARD_USER = 'standard_user', 'Standard User'
    APP_ADMIN = 'app_admin', 'App Admin'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def normalize_identity(self, email):
        return self.normalize_email(email.strip()).lower()

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The email address must be set.')

        email = self.normalize_identity(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.STANDARD_USER)
        extra_fields.setdefault('auth_source', AuthSource.LOCAL if password else AuthSource.ENTRA)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('role', UserRole.APP_ADMIN)
        extra_fields.setdefault('auth_source', AuthSource.LOCAL)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_local', True)
        return self._create_user(email, password, **extra_fields)


class User(UUIDTimestampedModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255)
    auth_source = models.CharField(max_length=16, choices=AuthSource.choices, default=AuthSource.LOCAL)
    role = models.CharField(max_length=32, choices=UserRole.choices, default=UserRole.STANDARD_USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_local = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ('email',)

    def save(self, *args, **kwargs):
        self.email = User.objects.normalize_identity(self.email)
        self.is_staff = self.is_staff or self.role == UserRole.APP_ADMIN
        self.is_local = self.is_local or self.auth_source == AuthSource.LOCAL
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email