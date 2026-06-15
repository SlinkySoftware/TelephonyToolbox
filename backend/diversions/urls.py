from django.urls import path

from diversions.views import (
    AdminDiversionDetailView,
    AdminDiversionListCreateView,
    AdminDiversionValidateSourceView,
    RefreshDiversionView,
    UpdateDestinationView,
    ValidateDestinationView,
    VisibleDiversionDetailView,
    VisibleDiversionListView,
)


urlpatterns = [
    path('diversions/', VisibleDiversionListView.as_view(), name='diversion-list'),
    path('diversions/<uuid:diversion_id>/', VisibleDiversionDetailView.as_view(), name='diversion-detail'),
    path('diversions/<uuid:diversion_id>/validate-destination/', ValidateDestinationView.as_view(), name='diversion-validate-destination'),
    path('diversions/<uuid:diversion_id>/update-destination/', UpdateDestinationView.as_view(), name='diversion-update-destination'),
    path('diversions/<uuid:diversion_id>/refresh/', RefreshDiversionView.as_view(), name='diversion-refresh'),
    path('admin/diversions/', AdminDiversionListCreateView.as_view(), name='admin-diversion-list'),
    path('admin/diversions/validate-source/', AdminDiversionValidateSourceView.as_view(), name='admin-diversion-validate-source'),
    path('admin/diversions/<uuid:diversion_id>/', AdminDiversionDetailView.as_view(), name='admin-diversion-detail'),
]