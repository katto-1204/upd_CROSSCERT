"""
Views for Event app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Event, EventRegistration, CheckIn
from .serializers import EventSerializer, EventRegistrationSerializer, CheckInSerializer
from crosscert.email_utils import (
    send_registration_confirmation,
    send_attendance_confirmation,
    send_post_event_evaluation_email,
    send_event_created_notification,
)
import qrcode
import io
import base64
import uuid
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPM


def _generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def _generate_barcode_image(data: str) -> str:
    barcode = code128.Code128(data, barHeight=40, barWidth=1.2)
    drawing = Drawing(barcode.width + 20, barcode.height + 20)
    drawing.add(barcode, name='barcode')
    png_bytes = renderPM.drawToString(drawing, fmt='PNG')
    return base64.b64encode(png_bytes).decode()


def _build_registration_code(registration: EventRegistration) -> str:
    """
    Build a per-participant code that encodes the event prefix and
    the participant's registration ID so each user has their own ID.
    Example: CBC-000123
    """
    event = registration.event
    prefix = event.generate_code_prefix()
    return f"{prefix}-{registration.id:06d}"


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for Event CRUD operations."""
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def perform_create(self, serializer):
        """Attach organizer and bootstrap event QR metadata."""
        user_model = get_user_model()
        organizer = self.request.user if self.request.user.is_authenticated else user_model.objects.first()
        event = serializer.save(organizer=organizer)

        event.generate_code_prefix()
        registration_url = event.build_registration_link()
        event.registration_url = registration_url
        event.event_qr_code = _generate_qr_code(registration_url)
        event.save(update_fields=['code_prefix', 'registration_url', 'event_qr_code'])

        # Notify organizer that event has been created
        organizer_email = getattr(organizer, "email", None)
        send_event_created_notification(
            event_title=event.title,
            event_date=str(event.date),
            organizer_email=organizer_email,
        )

    @action(detail=True, methods=['get'])
    def registrations(self, request, pk=None):
        """Get all registrations for an event."""
        event = self.get_object()
        registrations = event.registrations.all()
        serializer = EventRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)


class EventRegistrationViewSet(viewsets.ModelViewSet):
    """ViewSet for Event Registration management."""
    queryset = EventRegistration.objects.all()
    serializer_class = EventRegistrationSerializer

    def create(self, request, *args, **kwargs):
        """Register a participant for an event."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = serializer.save()
        # Ensure the registration has a primary key before building the code
        registration.refresh_from_db()
        code_value = _build_registration_code(registration)
        registration.qr_code_value = code_value
        registration.qr_code = _generate_qr_code(code_value)
        registration.barcode_image = _generate_barcode_image(code_value)
        registration.save(update_fields=['qr_code_value', 'qr_code', 'barcode_image'])

        # Send registration confirmation email
        event = registration.event
        event_time = f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}"
        participant_name = f"{registration.first_name} {registration.last_name}".strip()
        send_registration_confirmation(
            participant_name=participant_name or "Participant",
            event_title=event.title,
            event_date=event.date.strftime('%B %d, %Y'),
            event_time=event_time,
            venue=event.location,
            to_email=registration.email,
        )

        response_serializer = self.get_serializer(registration)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CheckInViewSet(viewsets.ModelViewSet):
    """ViewSet for Check-In management."""
    queryset = CheckIn.objects.all()
    serializer_class = CheckInSerializer

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """Check in a participant using registration ID."""
        registration_id = request.data.get('registration_id')

        try:
            registration = EventRegistration.objects.get(id=registration_id)
            check_in, created = CheckIn.objects.get_or_create(registration=registration)
            
            if not created:
                return Response(
                    {'message': 'Already checked in'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = self.get_serializer(check_in)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except EventRegistration.DoesNotExist:
            return Response(
                {'error': 'Registration not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='check-in-by-code')
    def check_in_by_code(self, request):
        """Check in using the participant QR/barcode value (CBC-XXXXXX)."""
        code_value = request.data.get('code')
        if not code_value:
            return Response({'error': 'Code is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            registration = EventRegistration.objects.get(qr_code_value=code_value)
        except EventRegistration.DoesNotExist:
            return Response({'error': 'Registration not found'}, status=status.HTTP_404_NOT_FOUND)

        check_in, created = CheckIn.objects.get_or_create(registration=registration)
        if not created and check_in.check_out_at is None:
            return Response({'message': 'Already checked in'}, status=status.HTTP_400_BAD_REQUEST)

        # Attendance confirmation email (first time only)
        if created:
            event = registration.event
            participant_name = f"{registration.first_name} {registration.last_name}".strip()
            send_attendance_confirmation(
                participant_name=participant_name or "Participant",
                event_title=event.title,
                event_date=event.date.strftime('%B %d, %Y'),
                venue=event.location,
                to_email=registration.email,
            )

        serializer = self.get_serializer(check_in)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='check-out-by-code')
    def check_out_by_code(self, request):
        """Check out a participant using the same QR/barcode value."""
        from django.utils import timezone

        code_value = request.data.get('code')
        if not code_value:
            return Response({'error': 'Code is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            registration = EventRegistration.objects.get(qr_code_value=code_value)
        except EventRegistration.DoesNotExist:
            return Response({'error': 'Registration not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            check_in = CheckIn.objects.get(registration=registration)
        except CheckIn.DoesNotExist:
            return Response({'error': 'Participant has not checked in yet'}, status=status.HTTP_400_BAD_REQUEST)

        if check_in.check_out_at is not None:
            return Response({'message': 'Already checked out'}, status=status.HTTP_400_BAD_REQUEST)

        check_in.check_out_at = timezone.now()
        check_in.save(update_fields=['check_out_at'])

        # Send post-event evaluation email with link
        event = registration.event
        frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
        eval_url = f"{frontend_base}/participant/event/{event.id}/evaluation"
        participant_name = f"{registration.first_name} {registration.last_name}".strip()
        send_post_event_evaluation_email(
            participant_name=participant_name or "Participant",
            event_title=event.title,
            evaluation_url=eval_url,
            to_email=registration.email,
        )

        serializer = self.get_serializer(check_in)
        return Response(serializer.data, status=status.HTTP_200_OK)
