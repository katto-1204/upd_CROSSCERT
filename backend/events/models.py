"""
Event models for CROSSCERT.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.conf import settings
import uuid


def default_certificate_coordinates():
    """Provide sane defaults so admins can preview overlays immediately."""
    return {
        'name': {'x': 561, 'y': 420},
        'event_title': {'x': 561, 'y': 360},
        'date': {'x': 561, 'y': 300},
    }


def default_certificate_sample_text():
    return {
        'name': 'Juan Dela Cruz',
        'event_title': 'Sample Event Title',
        'date': 'January 01, 2025',
    }


class Event(models.Model):
    """Event model for managing seminars and workshops."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
    ]

    CATEGORY_CHOICES = [
        ('HCDC', 'HCDC Wide Event'),
        ('department', 'Department Event'),
        ('outside', 'Outside Event'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255)
    capacity = models.IntegerField(default=50, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    speakers = models.JSONField(default=list, blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Manila')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='HCDC')
    department = models.CharField(max_length=120, blank=True)
    theme = models.CharField(max_length=50, default='Professional Blue')
    cover_image = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    require_approval = models.BooleanField(default=False)
    is_paid_event = models.BooleanField(default=False)
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    code_prefix = models.CharField(max_length=16, blank=True)
    registration_url = models.URLField(blank=True)
    event_qr_code = models.TextField(blank=True)
    certificate_template_image = models.TextField(blank=True)
    certificate_coordinates = models.JSONField(default=default_certificate_coordinates, blank=True)
    certificate_sample_text = models.JSONField(default=default_certificate_sample_text, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.title

    def generate_code_prefix(self):
        """Generate the 3-letter prefix derived from the event title."""
        if self.code_prefix:
            return self.code_prefix

        parts = [word[0].upper() for word in self.title.split() if word]
        prefix = ''.join(parts[:3])
        prefix = (prefix + 'EVT')[:3] if len(prefix) < 3 else prefix[:3]
        self.code_prefix = prefix
        return self.code_prefix

    def build_registration_link(self):
        """Generate the canonical registration URL for QR linking."""
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
        slug = slugify(self.title) or uuid.uuid4().hex[:6]
        return f"{base_url}/event/{self.id or slug}"


class EventRegistration(models.Model):
    """Event registration model for participants."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=100)
    registered_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.TextField(blank=True)
    qr_code_value = models.CharField(max_length=64, unique=True, null=True, blank=True)
    barcode_image = models.TextField(blank=True)

    class Meta:
        unique_together = ('event', 'email')

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.event.title}"


class CheckIn(models.Model):
    """Check-in model for attendance tracking."""
    registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name='check_in')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    check_out_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.registration.first_name} - {self.registration.event.title}"
