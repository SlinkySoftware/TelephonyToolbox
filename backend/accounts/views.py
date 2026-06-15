from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuthSource
from accounts.permissions import IsAppAdmin
from accounts.serializers import (
    AdminUserReadSerializer,
    AdminUserWriteSerializer,
    CurrentUserSerializer,
    ExternalValidationRequestSerializer,
    LoginSerializer,
    sync_memberships,
)
from accounts.services import (
    EntraOidcService,
    ExternalIdentityUnavailableError,
    IdentityValidationService,
    frontend_error_redirect,
    normalize_email,
    sync_external_user,
)
from audit.services import AuditService


User = get_user_model()
MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'
LOGIN_SUCCESS_EVENT = 'auth.login.success'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AuthOptionsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                'auth_mode': settings.AUTH_MODE,
                'local_auth_enabled': settings.LOCAL_AUTH_ENABLED,
            }
        )


class CurrentUserView(APIView):
    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


class LocalLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.LOCAL_AUTH_ENABLED:
            return Response({'message': 'Local authentication is disabled.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = normalize_email(serializer.validated_data['email'])
        user = authenticate(request, username=email, password=serializer.validated_data['password'])

        if user is None or not user.is_local or not user.is_active:
            AuditService.record_event(
                event_type='auth.login.failure',
                result='failure',
                actor_email=email,
                object_type='auth',
                object_name='local',
                message='Local login failed.',
            )
            return Response({'message': 'Invalid login credentials.'}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user, backend=MODEL_BACKEND)
        AuditService.record_event(
            event_type=LOGIN_SUCCESS_EVENT,
            result='success',
            actor=user,
            object_type='auth',
            object_name='local',
            message='Local login succeeded.',
        )
        return Response(CurrentUserSerializer(user).data)


class LdapLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if settings.AUTH_MODE != 'ldap':
            return Response({'message': 'LDAP authentication is not enabled.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = normalize_email(serializer.validated_data['email'])

        try:
            identity = IdentityValidationService.current_provider().authenticate_user(email, serializer.validated_data['password'])
        except ExternalIdentityUnavailableError:
            return Response({'message': 'LDAP is currently unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not identity.exists or not identity.enabled:
            AuditService.record_event(
                event_type='auth.login.failure',
                result='failure',
                actor_email=email,
                object_type='auth',
                object_name='ldap',
                message='LDAP login failed.',
            )
            return Response({'message': 'Invalid login credentials.'}, status=status.HTTP_400_BAD_REQUEST)

        user = sync_external_user(identity)
        if user is None or not user.is_active:
            return Response({'message': 'User is not provisioned for Telephony Toolbox.'}, status=status.HTTP_403_FORBIDDEN)

        login(request, user, backend=MODEL_BACKEND)
        AuditService.record_event(
            event_type=LOGIN_SUCCESS_EVENT,
            result='success',
            actor=user,
            object_type='auth',
            object_name='ldap',
            message='LDAP login succeeded.',
        )
        return Response(CurrentUserSerializer(user).data)


class EntraLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if settings.AUTH_MODE != 'entra':
            return Response({'message': 'Entra authentication is not enabled.'}, status=status.HTTP_404_NOT_FOUND)
        return EntraOidcService.authorize_redirect(request)


class EntraCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if settings.AUTH_MODE != 'entra':
            return HttpResponseRedirect(frontend_error_redirect('entra_disabled'))

        try:
            identity = EntraOidcService.handle_callback(request)
        except ExternalIdentityUnavailableError as exc:
            return HttpResponseRedirect(frontend_error_redirect(str(exc)))

        user = sync_external_user(identity)
        if user is None or not user.is_active:
            return HttpResponseRedirect(frontend_error_redirect('not_provisioned'))

        login(request, user, backend=MODEL_BACKEND)
        AuditService.record_event(
            event_type=LOGIN_SUCCESS_EVENT,
            result='success',
            actor=user,
            object_type='auth',
            object_name='entra',
            message='Entra login succeeded.',
        )
        return HttpResponseRedirect('/')


class LogoutView(APIView):
    def post(self, request):
        AuditService.record_event(
            event_type='auth.logout',
            result='success',
            actor=request.user,
            object_type='auth',
            object_name='session',
            message='User logged out.',
        )
        logout(request)
        return Response({'message': 'Logged out successfully.'})


class AdminUserValidateView(APIView):
    permission_classes = [IsAppAdmin]

    def post(self, request):
        serializer = ExternalValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = IdentityValidationService.validate_user(serializer.validated_data['email'])
        except ExternalIdentityUnavailableError:
            return Response({'message': 'External identity provider is unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        AuditService.record_event(
            event_type='user.validated.success' if result.exists else 'user.validated.failure',
            result='success' if result.exists else 'failure',
            actor=request.user,
            object_type='user',
            object_name=result.email,
            message='External user validation completed.',
            metadata={k: v for k, v in result.as_dict().items() if k != 'provider'},
        )
        return Response(result.as_dict())


class AdminUserListCreateView(APIView):
    permission_classes = [IsAppAdmin]

    def get(self, request):
        queryset = User.objects.all().order_by('email')
        search_term = request.query_params.get('search', '').strip()
        if search_term:
            queryset = queryset.filter(Q(email__icontains=search_term) | Q(display_name__icontains=search_term))
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        auth_source = request.query_params.get('auth_source')
        if auth_source:
            queryset = queryset.filter(auth_source=auth_source)
        return Response(AdminUserReadSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = AdminUserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        email = normalize_email(payload['email'])

        if payload['auth_source'] != AuthSource.LOCAL:
            try:
                identity = IdentityValidationService.validate_user(email)
            except ExternalIdentityUnavailableError:
                return Response({'message': 'External identity provider is unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            if not identity.exists or not identity.enabled:
                return Response({'message': 'External user validation failed.'}, status=status.HTTP_400_BAD_REQUEST)
            display_name = identity.display_name or payload['display_name']
        else:
            display_name = payload['display_name']

        user = User.objects.create_user(
            email=email,
            password=payload.get('password'),
            display_name=display_name,
            auth_source=payload['auth_source'],
            role=payload['role'],
            is_active=payload.get('is_active', True),
            is_local=payload['auth_source'] == AuthSource.LOCAL,
        )
        sync_memberships(user, payload.get('group_ids', []))

        AuditService.record_event(
            event_type='user.created',
            result='success',
            actor=request.user,
            object_type='user',
            object_id_text=str(user.pk),
            object_name=user.email,
            message='User created successfully.',
        )
        return Response(AdminUserReadSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(APIView):
    permission_classes = [IsAppAdmin]

    def get_object(self, user_id):
        return get_object_or_404(User, pk=user_id)

    def get(self, request, user_id):
        user = self.get_object(user_id)
        return Response(AdminUserReadSerializer(user).data)

    def patch(self, request, user_id):
        user = self.get_object(user_id)
        serializer = AdminUserWriteSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        for field in ('display_name', 'role', 'is_active'):
            if field in payload:
                setattr(user, field, payload[field])

        if 'auth_source' in payload:
            user.auth_source = payload['auth_source']
            user.is_local = payload['auth_source'] == AuthSource.LOCAL
        if payload.get('password'):
            user.set_password(payload['password'])

        user.save()
        if 'group_ids' in payload:
            sync_memberships(user, payload['group_ids'])

        AuditService.record_event(
            event_type='user.updated',
            result='success',
            actor=request.user,
            object_type='user',
            object_id_text=str(user.pk),
            object_name=user.email,
            message='User updated successfully.',
        )
        return Response(AdminUserReadSerializer(user).data)

    def delete(self, request, user_id):
        user = self.get_object(user_id)
        AuditService.record_event(
            event_type='user.deleted',
            result='success',
            actor=request.user,
            object_type='user',
            object_id_text=str(user.pk),
            object_name=user.email,
            message='User deleted successfully.',
        )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)