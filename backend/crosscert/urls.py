"""
URL configuration for CROSSCERT project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from events.views import EventViewSet, EventRegistrationViewSet, CheckInViewSet
from participants.views import ParticipantViewSet, EvaluationViewSet
from certificates.views import CertificateViewSet

# General API router for public/participant endpoints
api_router = DefaultRouter()
api_router.register(r'events', EventViewSet, basename='event')
api_router.register(r'registrations', EventRegistrationViewSet, basename='registration')
api_router.register(r'check-ins', CheckInViewSet, basename='check-in')
api_router.register(r'evaluations', EvaluationViewSet, basename='evaluation')
api_router.register(r'certificates', CertificateViewSet, basename='certificate')

# Admin API router for admin-specific endpoints
admin_router = DefaultRouter()
admin_router.register(r'events', EventViewSet, basename='admin-event')
admin_router.register(r'participants', ParticipantViewSet, basename='admin-participant')
admin_router.register(r'check-ins', CheckInViewSet, basename='admin-check-in')
admin_router.register(r'evaluations', EvaluationViewSet, basename='admin-evaluation')
admin_router.register(r'certificates', CertificateViewSet, basename='admin-certificate')

urlpatterns = [
    # Redirect root to Django admin for convenience during development
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include(api_router.urls)),
    path('api/admin/', include(admin_router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]
