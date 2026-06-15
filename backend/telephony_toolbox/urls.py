from django.urls import include, path

urlpatterns = [
    path('api/', include('accounts.urls')),
    path('api/', include('access_groups.urls')),
    path('api/', include('audit.urls')),
    path('api/', include('diversions.urls')),
    path('api/', include('health.urls')),
]
