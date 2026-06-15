# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import AuthSource, UserRole


class Command(BaseCommand):
    help = 'Creates or updates the first local App Admin account.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--display-name', required=True)
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        user_model = get_user_model()
        email = user_model.objects.normalize_identity(options['email'])
        password = options['password']
        if len(password) < 8:
            raise CommandError('Bootstrap App Admin passwords must be at least 8 characters long.')

        user, created = user_model.objects.get_or_create(
            email=email,
            defaults={
                'display_name': options['display_name'],
                'auth_source': AuthSource.LOCAL,
                'role': UserRole.APP_ADMIN,
                'is_local': True,
                'is_active': True,
            },
        )

        user.display_name = options['display_name']
        user.auth_source = AuthSource.LOCAL
        user.role = UserRole.APP_ADMIN
        user.is_local = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} local App Admin {email}.'))