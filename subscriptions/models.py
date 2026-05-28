import math
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class SubscriptionPlan(models.Model):
    tier = models.SlugField(
        max_length=64,
        unique=True,
        help_text='Stable plan identifier used in checkout URLs, Polar metadata, and API responses.',
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    benefit_lines = models.TextField(
        blank=True,
        help_text='Optional website benefit copy, one benefit per line.',
    )
    monthly_price_usd = models.PositiveIntegerField()
    monthly_server_minutes = models.PositiveIntegerField()
    max_session_minutes = models.PositiveIntegerField()
    max_concurrent_servers = models.PositiveIntegerField(default=1)
    polar_product_id = models.CharField(max_length=128, blank=True)
    discord_role_id = models.CharField(max_length=64, blank=True)
    entitlement_priority = models.IntegerField(
        default=0,
        help_text='Higher priority wins when a user has multiple active entitlements.',
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'monthly_price_usd', 'name']

    def __str__(self):
        return self.name

    @property
    def benefits(self):
        return [line.strip() for line in self.benefit_lines.splitlines() if line.strip()]


class SubscriptionEntitlement(models.Model):
    PROVIDER_POLAR = 'polar'
    PROVIDER_DISCORD = 'discord_server_subscription'
    PROVIDER_GITHUB = 'github_sponsors'
    PROVIDER_COMP = 'comp'

    STATUS_ACTIVE = 'active'
    STATUS_TRIALING = 'trialing'
    STATUS_PAST_DUE = 'past_due'
    STATUS_CANCELED = 'canceled'
    STATUS_EXPIRED = 'expired'
    STATUS_INACTIVE = 'inactive'

    PROVIDER_CHOICES = [
        (PROVIDER_POLAR, 'Polar'),
        (PROVIDER_DISCORD, 'Discord Server Subscription'),
        (PROVIDER_GITHUB, 'GitHub Sponsors'),
        (PROVIDER_COMP, 'Comp'),
    ]

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_TRIALING, 'Trialing'),
        (STATUS_PAST_DUE, 'Past Due'),
        (STATUS_CANCELED, 'Canceled'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription_entitlements')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='entitlements')
    provider = models.CharField(max_length=40, choices=PROVIDER_CHOICES)
    provider_customer_id = models.CharField(max_length=128, blank=True)
    provider_subscription_id = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    latest_event_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['provider', 'provider_subscription_id']),
            models.Index(fields=['current_period_end']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_subscription_id'],
                condition=~Q(provider_subscription_id=''),
                name='unique_subscription_provider_subscription',
            ),
        ]

    def __str__(self):
        return f'{self.user} - {self.plan.name} ({self.status})'

    @property
    def is_active(self) -> bool:
        return self.status in {self.STATUS_ACTIVE, self.STATUS_TRIALING} and self.current_period_end > timezone.now()

    @property
    def monthly_server_minutes(self) -> int:
        return self.plan.monthly_server_minutes

    @property
    def max_session_minutes(self) -> int:
        return self.plan.max_session_minutes

    @property
    def max_concurrent_servers(self) -> int:
        return self.plan.max_concurrent_servers


class ServerSession(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_LAUNCHING = 'launching'
    STATUS_RUNNING = 'running'
    STATUS_STOPPING = 'stopping'
    STATUS_STOPPED = 'stopped'
    STATUS_FAILED = 'failed'
    STATUS_EXPIRED = 'expired'
    STATUS_KILLED = 'killed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_LAUNCHING, 'Launching'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_STOPPING, 'Stopping'),
        (STATUS_STOPPED, 'Stopped'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_KILLED, 'Killed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='premium_server_sessions')
    entitlement = models.ForeignKey(SubscriptionEntitlement, on_delete=models.PROTECT, related_name='server_sessions')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    requested_minutes = models.PositiveIntegerField()
    allocated_minutes = models.PositiveIntegerField()
    game = models.CharField(max_length=80, blank=True)
    game_code = models.CharField(max_length=32, blank=True)
    comment = models.CharField(max_length=120, blank=True)
    server_identifier = models.CharField(max_length=128, blank=True)
    orchestrator_session_id = models.CharField(max_length=128, blank=True)
    orchestrator_state = models.CharField(max_length=64, blank=True)
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True)
    server_password = models.CharField(max_length=80, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    orchestrator_stopped_at = models.DateTimeField(null=True, blank=True)
    launch_error_code = models.CharField(max_length=80, blank=True)
    launch_error_message = models.TextField(blank=True)
    launch_context = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    last_heartbeat_at = models.DateTimeField(default=timezone.now)
    stopped_at = models.DateTimeField(null=True, blank=True)
    stop_reason = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['last_heartbeat_at']),
        ]

    def __str__(self):
        return f'{self.user} - {self.status} - {self.started_at}'

    @property
    def is_open(self) -> bool:
        return self.status in {
            self.STATUS_PENDING,
            self.STATUS_LAUNCHING,
            self.STATUS_RUNNING,
            self.STATUS_STOPPING,
        }

    def rounded_runtime_minutes(self, stopped_at=None) -> int:
        end_time = stopped_at or self.stopped_at or timezone.now()
        start_time = self.ready_at or self.started_at
        elapsed = max((end_time - start_time).total_seconds(), 0)
        rounded = int(math.ceil(elapsed / 300.0) * 5)
        return min(max(rounded, 5), self.allocated_minutes)

    def expires_at(self):
        return (self.ready_at or self.started_at) + timedelta(minutes=self.allocated_minutes)


class UsageLedgerEntry(models.Model):
    REASON_SERVER_SESSION = 'server_session'
    REASON_ADMIN_ADJUSTMENT = 'admin_adjustment'

    REASON_CHOICES = [
        (REASON_SERVER_SESSION, 'Server Session'),
        (REASON_ADMIN_ADJUSTMENT, 'Admin Adjustment'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='premium_usage_entries')
    entitlement = models.ForeignKey(SubscriptionEntitlement, on_delete=models.CASCADE, related_name='usage_entries')
    server_session = models.OneToOneField(ServerSession, on_delete=models.SET_NULL, related_name='usage_entry', null=True, blank=True)
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    minutes = models.IntegerField()
    reason = models.CharField(max_length=32, choices=REASON_CHOICES)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'billing_period_start', 'billing_period_end']),
        ]

    def __str__(self):
        return f'{self.user} - {self.minutes} minutes - {self.reason}'


class WebhookEvent(models.Model):
    STATUS_PROCESSED = 'processed'
    STATUS_SKIPPED = 'skipped'
    STATUS_FAILED = 'failed'

    provider = models.CharField(max_length=40)
    event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default=STATUS_PROCESSED)
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['provider', 'event_id'], name='unique_subscription_webhook_event'),
        ]
        ordering = ['-received_at']

    def __str__(self):
        return f'{self.provider}:{self.event_type}:{self.event_id}'
