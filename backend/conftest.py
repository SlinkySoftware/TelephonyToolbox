# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest
from rest_framework.test import APIClient

from access_groups.models import AccessGroup, UserGroupMembership
from accounts.models import AuthSource, User, UserRole
from diversions.models import Diversion

TEST_LOGIN_SECRET = 'Passw0rd!'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        email='admin@example.com',
        display_name='Admin User',
        auth_source=AuthSource.LOCAL,
        role=UserRole.APP_ADMIN,
        is_local=True,
    )
    user.set_password(TEST_LOGIN_SECRET)
    user.save()
    return user


@pytest.fixture
def standard_user(db):
    user = User.objects.create_user(
        email='operator@example.com',
        display_name='Operator User',
        auth_source=AuthSource.LOCAL,
        role=UserRole.STANDARD_USER,
        is_local=True,
    )
    user.set_password(TEST_LOGIN_SECRET)
    user.save()
    return user


@pytest.fixture
def access_group(db):
    return AccessGroup.objects.create(name='Retail Operations', description='Retail support team')


@pytest.fixture
def standard_user_membership(standard_user, access_group):
    return UserGroupMembership.objects.create(user=standard_user, group=access_group)


@pytest.fixture
def diversion(access_group, admin_user):
    return Diversion.objects.create(
        name='Retail Support Main Line',
        description='After-hours diversion',
        source_number='0299990000',
        source_partition='INTERNAL',
        cached_current_destination='+61288881111',
        group=access_group,
        created_by_text=admin_user.email,
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(admin_user)
    return api_client


@pytest.fixture
def standard_client(api_client, standard_user):
    api_client.force_authenticate(standard_user)
    return api_client