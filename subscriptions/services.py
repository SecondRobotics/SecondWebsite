import base64
import hashlib
import hmac
import json
from datetime import timedelta, timezone as datetime_timezone

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from discordoauth2.models import User
from .models import (
    ServerSession,
    SubscriptionEntitlement,
    SubscriptionPlan,
    UsageLedgerEntry,
    WebhookEvent,
)
from . import orchestrator


ACTIVE_STATUSES = {
    SubscriptionEntitlement.STATUS_ACTIVE,
    SubscriptionEntitlement.STATUS_TRIALING,
}

OPEN_SESSION_STATUSES = {
    ServerSession.STATUS_PENDING,
    ServerSession.STATUS_LAUNCHING,
    ServerSession.STATUS_RUNNING,
    ServerSession.STATUS_STOPPING,
}

TERMINAL_SESSION_STATUSES = {
    ServerSession.STATUS_STOPPED,
    ServerSession.STATUS_FAILED,
    ServerSession.STATUS_EXPIRED,
    ServerSession.STATUS_KILLED,
}

POLAR_STATUS_MAP = {
    'active': SubscriptionEntitlement.STATUS_ACTIVE,
    'trialing': SubscriptionEntitlement.STATUS_TRIALING,
    'past_due': SubscriptionEntitlement.STATUS_PAST_DUE,
    'unpaid': SubscriptionEntitlement.STATUS_PAST_DUE,
    'canceled': SubscriptionEntitlement.STATUS_CANCELED,
    'cancelled': SubscriptionEntitlement.STATUS_CANCELED,
    'revoked': SubscriptionEntitlement.STATUS_EXPIRED,
    'ended': SubscriptionEntitlement.STATUS_EXPIRED,
    'expired': SubscriptionEntitlement.STATUS_EXPIRED,
    'incomplete': SubscriptionEntitlement.STATUS_INACTIVE,
}


class WebhookVerificationError(ValueError):
    pass


class SubscriptionError(ValueError):
    def __init__(self, message, status_code=403, code='SUBSCRIPTION_ERROR'):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def get_active_entitlement(user):
    now = timezone.now()
    entitlements = SubscriptionEntitlement.objects.filter(
        user=user,
        status__in=ACTIVE_STATUSES,
        current_period_end__gt=now,
    ).select_related('plan').order_by(
        '-plan__entitlement_priority',
        '-plan__monthly_price_usd',
        '-plan__monthly_server_minutes',
        'plan__display_order',
    )
    return entitlements.first()


def used_minutes(entitlement):
    return UsageLedgerEntry.objects.filter(
        entitlement=entitlement,
        billing_period_start=entitlement.current_period_start,
        billing_period_end=entitlement.current_period_end,
    ).aggregate(total=models_sum('minutes'))['total'] or 0


def models_sum(field_name):
    from django.db.models import Sum

    return Sum(field_name)


def remaining_minutes(entitlement):
    return max(entitlement.monthly_server_minutes - used_minutes(entitlement), 0)


def entitlement_payload(user):
    entitlement = get_active_entitlement(user)
    if entitlement is None:
        return {
            'active': False,
            'tier': None,
            'plan': None,
            'period_start': None,
            'period_end': None,
            'monthly_server_minutes': 0,
            'used_server_minutes': 0,
            'remaining_server_minutes': 0,
            'max_session_minutes': 0,
            'active_session': None,
        }

    active_session = ServerSession.objects.filter(user=user, status__in=OPEN_SESSION_STATUSES).first()
    used = used_minutes(entitlement)
    return {
        'active': True,
        'tier': entitlement.plan.tier,
        'plan': entitlement.plan.name,
        'period_start': entitlement.current_period_start,
        'period_end': entitlement.current_period_end,
        'monthly_server_minutes': entitlement.monthly_server_minutes,
        'used_server_minutes': used,
        'remaining_server_minutes': max(entitlement.monthly_server_minutes - used, 0),
        'max_session_minutes': entitlement.max_session_minutes,
        'max_concurrent_servers': entitlement.max_concurrent_servers,
        'provider': entitlement.provider,
        'cancel_at_period_end': entitlement.cancel_at_period_end,
        'active_session': serialize_session(active_session) if active_session else None,
    }


def serialize_session(session):
    if session is None:
        return None
    return {
        'id': str(session.id),
        'status': session.status,
        'game': session.game,
        'game_code': session.game_code,
        'comment': session.comment,
        'server_identifier': session.server_identifier,
        'orchestrator_session_id': session.orchestrator_session_id,
        'orchestrator_state': session.orchestrator_state,
        'host': session.host,
        'port': session.port,
        'password': session.server_password,
        'requested_minutes': session.requested_minutes,
        'allocated_minutes': session.allocated_minutes,
        'started_at': session.started_at,
        'ready_at': session.ready_at,
        'last_heartbeat_at': session.last_heartbeat_at,
        'stopped_at': session.stopped_at,
        'stop_reason': session.stop_reason,
        'launch_error_code': session.launch_error_code,
        'launch_error_message': session.launch_error_message,
        'expires_at': session.expires_at(),
    }


@transaction.atomic
def start_server_session(user, requested_minutes=None, game='', server_identifier='', launch_context=None, status=ServerSession.STATUS_RUNNING):
    entitlement = get_active_entitlement(user)
    if entitlement is None:
        raise SubscriptionError('An active premium subscription is required to launch a casual server.')

    running_sessions = ServerSession.objects.select_for_update().filter(
        user=user,
        status__in=OPEN_SESSION_STATUSES,
    ).count()
    if running_sessions >= entitlement.max_concurrent_servers:
        if entitlement.max_concurrent_servers == 1:
            raise SubscriptionError('You already have a casual server session running.')
        raise SubscriptionError('You have reached your plan limit for concurrent casual servers.')

    remaining = remaining_minutes(entitlement)
    if remaining <= 0:
        raise SubscriptionError('You have used all of your casual server hours for this billing period.')

    requested = requested_minutes or entitlement.max_session_minutes
    try:
        requested = int(requested)
    except (TypeError, ValueError) as exc:
        raise SubscriptionError('requested_minutes must be an integer.', status_code=400, code='INVALID_REQUESTED_MINUTES') from exc
    requested = max(requested, 5)
    allocated = min(requested, entitlement.max_session_minutes, remaining)

    session = ServerSession.objects.create(
        user=user,
        entitlement=entitlement,
        status=status,
        requested_minutes=requested,
        allocated_minutes=allocated,
        game=game or '',
        server_identifier=server_identifier or '',
        launch_context=launch_context or {},
    )
    return session


def _parse_datetime(value):
    if not value:
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else value
    if parsed and timezone.is_naive(parsed):
        return timezone.make_aware(parsed, datetime_timezone.utc)
    return parsed


def _actor_for_user(user, actor_type='website_user'):
    display_name = getattr(user, 'display_name', '') or getattr(user, 'username', '') or str(user.id)
    return {
        'type': actor_type,
        'discordUserId': str(user.id),
        'displayName': display_name,
    }


def _apply_orchestrator_payload(session, payload):
    details = payload.get('session') or payload.get('server') or payload
    if not isinstance(details, dict):
        return

    orchestrator_session_id = details.get('id') or details.get('sessionId') or details.get('orchestratorSessionId')
    if orchestrator_session_id:
        session.orchestrator_session_id = str(orchestrator_session_id)
        session.server_identifier = str(orchestrator_session_id)

    state = details.get('state') or details.get('status') or details.get('orchestratorState')
    if state:
        session.orchestrator_state = str(state)

    if details.get('host'):
        session.host = str(details['host'])
    if details.get('port') is not None:
        session.port = int(details['port'])
    if details.get('password'):
        session.server_password = str(details['password'])


@transaction.atomic
def reserve_server_session(user, requested_minutes=None, game='', game_code='', comment='', password='', launch_context=None):
    session = start_server_session(
        user,
        requested_minutes=requested_minutes,
        game=game,
        launch_context=launch_context,
        status=ServerSession.STATUS_PENDING,
    )
    session.game_code = str(game_code or '')
    session.comment = (comment or '')[:120]
    session.server_password = (password or '')[:80]
    session.save(update_fields=['game_code', 'comment', 'server_password', 'updated_at'])
    return session


def launch_casual_server(user, requested_minutes=None, game='', game_code='', comment='', password='', launch_source='website', launch_context=None):
    session = reserve_server_session(
        user,
        requested_minutes=requested_minutes,
        game=game,
        game_code=game_code,
        comment=comment,
        password=password,
        launch_context=launch_context,
    )

    try:
        payload = orchestrator.launch_casual(
            session,
            game_code=session.game_code,
            comment=session.comment,
            password=session.server_password,
            launch_source=launch_source,
            actor=_actor_for_user(user, actor_type='discord_bot' if launch_source == 'discord_bot' else 'website_user'),
        )
    except orchestrator.OrchestratorError as exc:
        mark_server_session_failed(session, exc.code, str(exc))
        raise SubscriptionError(str(exc), status_code=503, code=exc.code) from exc

    session = ServerSession.objects.get(pk=session.pk)
    _apply_orchestrator_payload(session, payload)
    session.status = ServerSession.STATUS_LAUNCHING
    session.save(update_fields=[
        'status',
        'orchestrator_session_id',
        'orchestrator_state',
        'host',
        'port',
        'server_password',
        'server_identifier',
        'updated_at',
    ])
    return session


@transaction.atomic
def mark_server_session_failed(session, code='', message=''):
    session = ServerSession.objects.select_for_update().get(pk=session.pk)
    if session.status in TERMINAL_SESSION_STATUSES:
        return session
    now = timezone.now()
    session.status = ServerSession.STATUS_FAILED
    session.stopped_at = now
    session.stop_reason = 'launch_failed'
    session.launch_error_code = code or ''
    session.launch_error_message = message or ''
    session.save(update_fields=[
        'status',
        'stopped_at',
        'stop_reason',
        'launch_error_code',
        'launch_error_message',
        'updated_at',
    ])
    return session


@transaction.atomic
def heartbeat_server_session(session, server_identifier=''):
    session = ServerSession.objects.select_for_update().get(pk=session.pk)
    if session.status not in OPEN_SESSION_STATUSES:
        raise SubscriptionError('This server session is not running.')
    session.last_heartbeat_at = timezone.now()
    if server_identifier:
        session.server_identifier = server_identifier
    session.save(update_fields=['last_heartbeat_at', 'server_identifier', 'updated_at'])
    return session


@transaction.atomic
def stop_server_session(session, reason='stopped'):
    session = ServerSession.objects.select_for_update().get(pk=session.pk)
    if session.status not in OPEN_SESSION_STATUSES:
        return session

    stopped_at = timezone.now()
    billed_minutes = session.rounded_runtime_minutes(stopped_at=stopped_at)
    session.status = ServerSession.STATUS_EXPIRED if reason == ServerSession.STATUS_EXPIRED else ServerSession.STATUS_STOPPED
    session.stopped_at = stopped_at
    session.stop_reason = reason or 'stopped'
    session.save(update_fields=['status', 'stopped_at', 'stop_reason', 'updated_at'])

    UsageLedgerEntry.objects.get_or_create(
        server_session=session,
        defaults={
            'user': session.user,
            'entitlement': session.entitlement,
            'billing_period_start': session.entitlement.current_period_start,
            'billing_period_end': session.entitlement.current_period_end,
            'minutes': billed_minutes,
            'reason': UsageLedgerEntry.REASON_SERVER_SESSION,
            'metadata': {'stop_reason': session.stop_reason},
        },
    )
    return session


def _rounded_runtime_minutes_from_seconds(runtime_seconds, allocated_minutes):
    elapsed = max(int(runtime_seconds or 0), 0)
    if elapsed <= 0:
        return 0
    rounded = int((elapsed + 299) // 300 * 5)
    return min(max(rounded, 5), allocated_minutes)


def _record_orchestrator_usage(session, stopped_at, runtime_seconds=None):
    if runtime_seconds is not None:
        billed_minutes = _rounded_runtime_minutes_from_seconds(runtime_seconds, session.allocated_minutes)
    elif session.ready_at:
        billed_minutes = session.rounded_runtime_minutes(stopped_at=stopped_at)
    else:
        billed_minutes = 0

    if billed_minutes <= 0:
        return None

    usage, _created = UsageLedgerEntry.objects.get_or_create(
        server_session=session,
        defaults={
            'user': session.user,
            'entitlement': session.entitlement,
            'billing_period_start': session.entitlement.current_period_start,
            'billing_period_end': session.entitlement.current_period_end,
            'minutes': billed_minutes,
            'reason': UsageLedgerEntry.REASON_SERVER_SESSION,
            'metadata': {'stop_reason': session.stop_reason, 'source': 'orchestrator'},
        },
    )
    return usage


@transaction.atomic
def process_orchestrator_event(session_id, payload):
    event_id = payload.get('event_id')
    event_type = payload.get('event')
    if not event_id or not event_type:
        raise SubscriptionError('Orchestrator events require event_id and event.')

    event, created = WebhookEvent.objects.get_or_create(
        provider='orchestrator',
        event_id=event_id,
        defaults={
            'event_type': event_type,
            'payload': payload,
            'status': WebhookEvent.STATUS_PROCESSED,
            'processed_at': timezone.now(),
        },
    )
    if not created:
        return event

    session = ServerSession.objects.select_for_update().get(pk=session_id)
    occurred_at = _parse_datetime(payload.get('occurred_at')) or timezone.now()

    if payload.get('orchestrator_session_id'):
        session.orchestrator_session_id = str(payload['orchestrator_session_id'])
        session.server_identifier = str(payload['orchestrator_session_id'])
    if payload.get('orchestrator_state'):
        session.orchestrator_state = str(payload['orchestrator_state'])
    if payload.get('host'):
        session.host = str(payload['host'])
    if payload.get('port') is not None:
        session.port = int(payload['port'])
    if payload.get('password'):
        session.server_password = str(payload['password'])

    if event_type == 'launch_accepted':
        session.status = ServerSession.STATUS_LAUNCHING
    elif event_type == 'ready':
        session.status = ServerSession.STATUS_RUNNING
        session.ready_at = _parse_datetime(payload.get('ready_at')) or occurred_at
        session.last_heartbeat_at = occurred_at
    elif event_type == 'heartbeat':
        if session.status not in TERMINAL_SESSION_STATUSES:
            session.status = ServerSession.STATUS_RUNNING
            session.last_heartbeat_at = occurred_at
    elif event_type == 'stopping':
        if session.status not in TERMINAL_SESSION_STATUSES:
            session.status = ServerSession.STATUS_STOPPING
            session.stop_reason = payload.get('reason') or 'stopping'
    elif event_type in {'stopped', 'exited', 'killed'}:
        stopped_at = _parse_datetime(payload.get('stopped_at')) or occurred_at
        session.status = ServerSession.STATUS_KILLED if event_type == 'killed' else ServerSession.STATUS_STOPPED
        session.stopped_at = stopped_at
        session.orchestrator_stopped_at = stopped_at
        session.stop_reason = payload.get('reason') or event_type
        runtime_seconds = payload.get('runtime_seconds')
        _record_orchestrator_usage(session, stopped_at, runtime_seconds=runtime_seconds)
    elif event_type == 'launch_failed':
        session.status = ServerSession.STATUS_FAILED
        session.stopped_at = occurred_at
        session.stop_reason = 'launch_failed'
        session.launch_error_code = payload.get('error_code') or ''
        session.launch_error_message = payload.get('error_message') or ''

    session.save(update_fields=[
        'status',
        'orchestrator_session_id',
        'orchestrator_state',
        'host',
        'port',
        'server_password',
        'server_identifier',
        'ready_at',
        'last_heartbeat_at',
        'stopped_at',
        'orchestrator_stopped_at',
        'stop_reason',
        'launch_error_code',
        'launch_error_message',
        'updated_at',
    ])
    return event


def request_stop_server_session(session, reason='stopped', actor=None):
    session = ServerSession.objects.get(pk=session.pk)
    if session.status in TERMINAL_SESSION_STATUSES:
        return session

    if session.orchestrator_session_id:
        try:
            orchestrator.stop_server(session.orchestrator_session_id, reason=reason, actor=actor)
        except orchestrator.OrchestratorError as exc:
            raise SubscriptionError(str(exc), status_code=503, code=exc.code) from exc
        session.status = ServerSession.STATUS_STOPPING
        session.stop_reason = reason or 'stopping'
        session.save(update_fields=['status', 'stop_reason', 'updated_at'])
        return session

    return stop_server_session(session, reason=reason)


def expire_stale_sessions(max_heartbeat_age_minutes=10):
    cutoff = timezone.now() - timedelta(minutes=max_heartbeat_age_minutes)
    stale_sessions = ServerSession.objects.filter(
        status=ServerSession.STATUS_RUNNING,
        last_heartbeat_at__lt=cutoff,
    )
    expired = []
    for session in stale_sessions:
        expired.append(stop_server_session(session, reason=ServerSession.STATUS_EXPIRED))
    return expired


def verify_standard_webhook_signature(secret, body, webhook_id, webhook_timestamp, webhook_signature):
    if not secret:
        raise WebhookVerificationError('Polar webhook secret is not configured.')
    if not webhook_id or not webhook_timestamp or not webhook_signature:
        raise WebhookVerificationError('Missing webhook signature headers.')

    try:
        timestamp = int(webhook_timestamp)
    except (TypeError, ValueError) as exc:
        raise WebhookVerificationError('Invalid webhook timestamp.') from exc

    if abs(int(timezone.now().timestamp()) - timestamp) > 300:
        raise WebhookVerificationError('Webhook timestamp is outside the replay window.')

    signing_secret = secret
    if signing_secret.startswith('whsec_'):
        signing_secret = signing_secret[len('whsec_'):]
    try:
        secret_bytes = base64.b64decode(signing_secret, validate=True)
    except Exception:
        secret_bytes = secret.encode('utf-8')

    signed_content = b'.'.join([
        webhook_id.encode('utf-8'),
        webhook_timestamp.encode('utf-8'),
        body,
    ])
    digest = hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    expected = 'v1,' + base64.b64encode(digest).decode('utf-8')

    signatures = webhook_signature.split(' ')
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise WebhookVerificationError('Invalid webhook signature.')


def process_polar_webhook(payload, event_id):
    event_type = payload.get('type') or payload.get('event') or ''
    data = payload.get('data') or {}

    event, created = WebhookEvent.objects.get_or_create(
        provider=SubscriptionEntitlement.PROVIDER_POLAR,
        event_id=event_id,
        defaults={
            'event_type': event_type,
            'payload': payload,
        },
    )
    if not created:
        return event

    try:
        if event_type.startswith('subscription.'):
            _upsert_entitlement_from_polar_subscription(data, event_id)
            event.status = WebhookEvent.STATUS_PROCESSED
        else:
            event.status = WebhookEvent.STATUS_SKIPPED
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'processed_at'])
    except Exception as exc:
        event.status = WebhookEvent.STATUS_FAILED
        event.error = str(exc)
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'error', 'processed_at'])
        raise
    return event


def create_polar_checkout_url(user, plan, customer_ip_address=''):
    token = getattr(settings, 'POLAR_ACCESS_TOKEN', '')
    if not token:
        raise SubscriptionError('Polar access token is not configured.')
    if not plan.polar_product_id:
        raise SubscriptionError(f'Polar product ID is not configured for {plan.name}.')

    payload = {
        'products': [plan.polar_product_id],
        'external_customer_id': str(user.id),
        'customer_email': user.email,
        'metadata': {
            'discord_user_id': str(user.id),
            'tier': plan.tier,
        },
    }
    success_url = getattr(settings, 'POLAR_CHECKOUT_SUCCESS_URL', '')
    if success_url:
        payload['success_url'] = success_url
    if customer_ip_address:
        payload['customer_ip_address'] = customer_ip_address

    response = requests.post(
        f'{settings.POLAR_API_BASE_URL}/v1/checkouts',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        data=json.dumps(payload),
        timeout=10,
    )
    if response.status_code >= 400:
        raise SubscriptionError('Polar checkout could not be created.')
    data = response.json()
    checkout_url = data.get('url')
    if not checkout_url:
        raise SubscriptionError('Polar checkout response did not include a checkout URL.')
    return checkout_url


def _upsert_entitlement_from_polar_subscription(data, event_id):
    user = _user_from_polar_data(data)
    plan = _plan_from_polar_data(data)
    if user is None or plan is None:
        raise SubscriptionError('Polar subscription webhook did not include a known user and plan.')

    subscription_id = str(data.get('id') or data.get('subscription_id') or '')
    if not subscription_id:
        raise SubscriptionError('Polar subscription webhook did not include a subscription ID.')

    period_start = _parse_dt(
        data.get('current_period_start')
        or data.get('started_at')
        or data.get('created_at')
    ) or timezone.now()
    period_end = _parse_dt(
        data.get('current_period_end')
        or data.get('ends_at')
        or data.get('ended_at')
    ) or (period_start + timedelta(days=31))
    raw_status = str(data.get('status') or '').lower()
    status = POLAR_STATUS_MAP.get(raw_status, SubscriptionEntitlement.STATUS_ACTIVE)

    customer = data.get('customer') or {}
    customer_id = str(data.get('customer_id') or customer.get('id') or '')

    SubscriptionEntitlement.objects.update_or_create(
        provider=SubscriptionEntitlement.PROVIDER_POLAR,
        provider_subscription_id=subscription_id,
        defaults={
            'user': user,
            'plan': plan,
            'provider_customer_id': customer_id,
            'status': status,
            'current_period_start': period_start,
            'current_period_end': period_end,
            'cancel_at_period_end': bool(data.get('cancel_at_period_end') or data.get('cancel_at_period') or False),
            'latest_event_id': event_id,
            'metadata': data,
        },
    )


def _user_from_polar_data(data):
    customer = data.get('customer') or {}
    metadata = data.get('metadata') or {}
    external_id = (
        data.get('external_customer_id')
        or data.get('customer_external_id')
        or customer.get('external_id')
        or metadata.get('discord_user_id')
    )
    if external_id is None:
        return None
    try:
        return User.objects.get(id=int(external_id))
    except (User.DoesNotExist, TypeError, ValueError, OverflowError):
        return None


def _plan_from_polar_data(data):
    metadata = data.get('metadata') or {}
    tier = metadata.get('tier')
    if tier:
        plan = SubscriptionPlan.objects.filter(tier=tier).first()
        if plan:
            return plan

    product_id = (
        data.get('product_id')
        or (data.get('product') or {}).get('id')
        or (data.get('products') or [{}])[0].get('id')
    )
    if product_id:
        plan = SubscriptionPlan.objects.filter(polar_product_id=product_id).first()
        if plan:
            return plan
    return None


def _parse_dt(value):
    if not value:
        return None
    if hasattr(value, 'tzinfo'):
        return value
    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, datetime_timezone.utc)
    return parsed
