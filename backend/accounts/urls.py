# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.urls import path

from accounts.views import (
    AdminUserDetailView,
    AdminUserListCreateView,
    AdminUserValidateView,
    AuthOptionsView,
    CurrentUserView,
    EntraCallbackView,
    EntraLoginView,
    LdapLoginView,
    LocalLoginView,
    OidcCallbackView,
    OidcLoginView,
    LogoutView,
)


urlpatterns = [
    path('auth/options/', AuthOptionsView.as_view(), name='auth-options'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('auth/login/entra/', EntraLoginView.as_view(), name='auth-entra-login'),
    path('auth/login/entra/callback/', EntraCallbackView.as_view(), name='auth-entra-callback'),
    path('auth/login/oidc/', OidcLoginView.as_view(), name='auth-oidc-login'),
    path('auth/login/oidc/callback/', OidcCallbackView.as_view(), name='auth-oidc-callback'),
    path('auth/login/ldap/', LdapLoginView.as_view(), name='auth-ldap-login'),
    path('auth/login/local/', LocalLoginView.as_view(), name='auth-local-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('admin/users/', AdminUserListCreateView.as_view(), name='admin-users'),
    path('admin/users/validate/', AdminUserValidateView.as_view(), name='admin-users-validate'),
    path('admin/users/<uuid:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
]