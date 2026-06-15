from django.urls import path

from health.views import AdminHealthView, HealthzView


urlpatterns = [
    path('healthz', HealthzView.as_view(), name='healthz'),
    path('admin/health/', AdminHealthView.as_view(), name='admin-health'),
]