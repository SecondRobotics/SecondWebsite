from datetime import timedelta, timezone as datetime_timezone

from django.conf import settings
from django.db import OperationalError, transaction
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
from . import polar_gateway
from .credits import lock_user, spendable_polar_balance


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
        current_period_start__lte=now,
        current_period_end__gt=now,
    ).select_related('plan').order_by(
        '-plan__entitlement_priority',
        '-plan__monthly_price_usd',
        '-plan__monthly_credits',
        'plan__display_order',
    )
    return entitlements.first()


def used_credits(entitlement):
    return UsageLedgerEntry.objects.filter(
        entitlement=entitlement,
        billing_period_start=entitlement.current_period_start,
        billing_period_end=entitlement.current_period_end,
    ).aggregate(total=models_sum('credits'))['total'] or 0


def models_sum(field_name):
    from django.db.models import Sum

    return Sum(field_name)


def locally_reserved_credits(entitlement):
    return ServerSession.objects.filter(
        user=entitlement.user,
        entitlement=entitlement,
        status__in=OPEN_SESSION_STATUSES,
    ).aggregate(total=models_sum('allocated_minutes'))['total'] or 0


def _polar_credit_balance(entitlement):
    try:
        return spendable_polar_balance(entitlement.user)
    except polar_gateway.PolarGatewayError as exc:
        raise SubscriptionError(str(exc), status_code=503, code='POLAR_CREDIT_BALANCE_UNAVAILABLE') from exc


def available_credits(entitlement):
    if entitlement.provider == SubscriptionEntitlement.PROVIDER_POLAR:
        return max(_polar_credit_balance(entitlement) - locally_reserved_credits(entitlement), 0)
    return max(entitlement.monthly_credits - used_credits(entitlement) - locally_reserved_credits(entitlement), 0)


def credit_summary(entitlement):
    if entitlement.provider == SubscriptionEntitlement.PROVIDER_POLAR:
        try:
            remaining = max(spendable_polar_balance(entitlement.user) - locally_reserved_credits(entitlement), 0)
            monthly = entitlement.monthly_credits
            return {
                'monthly_credits': monthly,
                'used_credits': max(monthly - remaining, 0),
                'remaining_credits': remaining,
                'reserved_credits': locally_reserved_credits(entitlement),
                'balance_source': 'polar',
                'balance_available': True,
            }
        except polar_gateway.PolarGatewayError:
            return {
                'monthly_credits': entitlement.monthly_credits,
                'used_credits': used_credits(entitlement),
                'remaining_credits': 0,
                'reserved_credits': locally_reserved_credits(entitlement),
                'balance_source': 'polar',
                'balance_available': False,
            }

    used = used_credits(entitlement)
    monthly = entitlement.monthly_credits
    reserved = locally_reserved_credits(entitlement)
    return {
        'monthly_credits': monthly,
        'used_credits': used,
        'remaining_credits': max(monthly - used - reserved, 0),
        'reserved_credits': reserved,
        'balance_source': 'local',
        'balance_available': True,
    }


def entitlement_payload(user):
    entitlement = get_active_entitlement(user)
    active_session = ServerSession.objects.filter(user=user, status__in=OPEN_SESSION_STATUSES).first()
    if entitlement is None:
        return {
            'active': False,
            'tier': None,
            'plan': None,
            'period_start': None,
            'period_end': None,
            'monthly_credits': 0,
            'used_credits': 0,
            'remaining_credits': 0,
            'reserved_credits': 0,
            'credit_balance_source': None,
            'credit_balance_available': False,
            'max_session_minutes': 0,
            'active_session': serialize_session(active_session),
        }

    credits = credit_summary(entitlement)
    return {
        'active': True,
        'tier': entitlement.plan.tier,
        'plan': entitlement.plan.name,
        'period_start': entitlement.current_period_start,
        'period_end': entitlement.current_period_end,
        'monthly_credits': credits['monthly_credits'],
        'used_credits': credits['used_credits'],
        'remaining_credits': credits['remaining_credits'],
        'reserved_credits': credits['reserved_credits'],
        'credit_balance_source': credits['balance_source'],
        'credit_balance_available': credits['balance_available'],
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
    lock_user(user.pk)
    entitlement = get_active_entitlement(user)
    if entitlement is None:
        raise SubscriptionError('An active premium subscription is required to launch a casual server.')
    entitlement = SubscriptionEntitlement.objects.select_for_update().select_related('plan').get(pk=entitlement.pk)

    running_sessions = ServerSession.objects.select_for_update().filter(
        user=user,
        status__in=OPEN_SESSION_STATUSES,
    ).count()
    if running_sessions >= entitlement.max_concurrent_servers:
        if entitlement.max_concurrent_servers == 1:
            raise SubscriptionError('You already have a casual server session running.')
        raise SubscriptionError('You have reached your plan limit for concurrent casual servers.')

    remaining = available_credits(entitlement)
    if remaining <= 0:
        raise SubscriptionError('You have used all of your casual server credits for this billing period.')

    requested = requested_minutes or entitlement.max_session_minutes
    try:
        requested = int(requested)
    except (TypeError, ValueError) as exc:
        raise SubscriptionError('requested_minutes must be an integer.', status_code=400, code='INVALID_REQUESTED_MINUTES') from exc
    requested = max(requested, 5)
    # Do not carry an old billing-cycle reservation into the next cycle. Leave
    # a minute for the launch request and the orchestrator's timeout polling.
    period_minutes = int((entitlement.current_period_end - timezone.now()).total_seconds() // 60) - 1
    if period_minutes < 5:
        raise SubscriptionError('This billing period ends shortly. Try again after renewal.')
    allocated = min(requested, entitlement.max_session_minutes, remaining, period_minutes)

    session = ServerSession.objects.create(
        user=user,
        entitlement=entitlement,
        status=status,
        requested_minutes=requested,
        allocated_minutes=allocated,
        billing_period_start=entitlement.current_period_start,
        billing_period_end=entitlement.current_period_end,
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
    session.comment = (comment or f'Casual {game_code}')[:120]
    session.server_password = (password or '')[:80]
    session.save(update_fields=['game_code', 'comment', 'server_password', 'updated_at'])
    return session


def launch_casual_server(user, requested_minutes=None, game='', game_code='', comment='', password='', launch_source='website', launch_context=None):
    try:
        session = reserve_server_session(
            user, requested_minutes=requested_minutes, game=game, game_code=game_code,
            comment=comment, password=password, launch_context=launch_context,
        )
    except OperationalError as exc:
        if 'locked' not in str(exc).lower():
            raise
        raise SubscriptionError('Another session update is in progress. Try again shortly.',
                                status_code=409, code='SESSION_UPDATE_IN_PROGRESS') from exc

    try:
        payload = orchestrator.launch_casual(
            session,
            game_code=session.game_code,
            comment=session.comment,
            password=session.server_password,
            launch_source=launch_source,
            actor=_actor_for_user(user, actor_type='discord_user' if launch_source == 'discord_bot' else 'website_user'),
        )
    except orchestrator.OrchestratorError as exc:
        # A timeout/5xx may follow a successful spawn. Keep the reservation so
        # reconciliation can recover by websiteServerSessionId.
        if (exc.status_code and 400 <= exc.status_code < 500) or exc.code == 'ORCHESTRATOR_NOT_CONFIGURED':
            mark_server_session_failed(session, exc.code, str(exc))
        raise SubscriptionError(str(exc), status_code=503, code=exc.code) from exc

    return _record_launch_response(session.pk, payload, user.pk)


@transaction.atomic
def _record_launch_response(session_id, payload, user_id):
    # Acquire the SQLite writer before reading a callback-updated session.
    lock_user(user_id)
    session = ServerSession.objects.select_for_update().get(pk=session_id)
    if session.status in TERMINAL_SESSION_STATUSES:
        return session
    previous_state = session.orchestrator_state
    _apply_orchestrator_payload(session, payload)
    if session.last_event_at:
        session.orchestrator_state = previous_state
    if session.status == ServerSession.STATUS_PENDING:
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
    lock_user(session.user_id)
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
def stop_server_session(session, reason='stopped'):
    lock_user(session.user_id)
    session = ServerSession.objects.select_for_update().get(pk=session.pk)
    if session.status not in OPEN_SESSION_STATUSES:
        return session

    stopped_at = timezone.now()
    billed_minutes = session.rounded_runtime_minutes(stopped_at=stopped_at)
    session.status = ServerSession.STATUS_EXPIRED if reason == ServerSession.STATUS_EXPIRED else ServerSession.STATUS_STOPPED
    session.stopped_at = stopped_at
    session.stop_reason = reason or 'stopped'
    session.save(update_fields=['status', 'stopped_at', 'stop_reason', 'updated_at'])

    _create_usage_entry(session, billed_minutes, {'stop_reason': session.stop_reason})
    return session


def _rounded_runtime_minutes_from_seconds(runtime_seconds, allocated_minutes):
    elapsed = max(int(runtime_seconds or 0), 0)
    if elapsed <= 0:
        return 0
    rounded = int((elapsed + 299) // 300 * 5)
    return min(max(rounded, 5), allocated_minutes)


def _create_usage_entry(session, credits, metadata):
    polar_required = session.entitlement.provider == SubscriptionEntitlement.PROVIDER_POLAR
    usage, created = UsageLedgerEntry.objects.get_or_create(
        server_session=session,
        defaults={
            'user': session.user,
            'entitlement': session.entitlement,
            'billing_period_start': session.billing_period_start or session.entitlement.current_period_start,
            'billing_period_end': session.billing_period_end or session.entitlement.current_period_end,
            'credits': credits,
            'reason': UsageLedgerEntry.REASON_SERVER_SESSION,
            'polar_status': UsageLedgerEntry.POLAR_STATUS_PENDING if polar_required else UsageLedgerEntry.POLAR_STATUS_NOT_REQUIRED,
            'metadata': {**metadata, 'polar_meter_id': getattr(settings, 'POLAR_CASUAL_SERVER_METER_ID', '')},
        },
    )
    # Persist first; the scheduled worker owns network ingestion.
    return usage


def sync_polar_usage_entry(usage):
    usage = UsageLedgerEntry.objects.select_related('entitlement', 'server_session', 'user').get(pk=usage.pk)
    if usage.entitlement.provider != SubscriptionEntitlement.PROVIDER_POLAR:
        return usage
    if usage.polar_status == UsageLedgerEntry.POLAR_STATUS_SENT:
        return usage
    if usage.server_session is None:
        usage.polar_status = UsageLedgerEntry.POLAR_STATUS_FAILED
        usage.polar_error = 'Usage entry is missing its server session.'
        usage.polar_last_attempt_at = timezone.now()
        usage.save(update_fields=['polar_status', 'polar_error', 'polar_last_attempt_at'])
        return usage

    usage.polar_last_attempt_at = timezone.now()
    try:
        response = polar_gateway.ingest_usage_event(
            usage.server_session,
            usage.credits,
            usage.server_session.stopped_at or usage.created_at or timezone.now(),
        )
    except polar_gateway.PolarGatewayError as exc:
        usage.polar_status = UsageLedgerEntry.POLAR_STATUS_FAILED
        usage.polar_error = str(exc)
        usage.save(update_fields=['polar_status', 'polar_error', 'polar_last_attempt_at'])
        return usage

    usage.polar_status = UsageLedgerEntry.POLAR_STATUS_SENT
    usage.polar_error = ''
    usage.metadata = {
        **usage.metadata,
        'polar_event_name': getattr(settings, 'POLAR_CASUAL_SERVER_EVENT_NAME', '') or 'casual_server_credits',
        'polar_inserted': getattr(response, 'inserted', None),
        'polar_duplicates': getattr(response, 'duplicates', None),
    }
    usage.save(update_fields=['polar_status', 'polar_error', 'polar_last_attempt_at', 'metadata'])
    return usage


def sync_pending_polar_usage(limit=100):
    pending = UsageLedgerEntry.objects.filter(
        entitlement__provider=SubscriptionEntitlement.PROVIDER_POLAR,
        polar_status__in=[
            UsageLedgerEntry.POLAR_STATUS_PENDING,
            UsageLedgerEntry.POLAR_STATUS_FAILED,
        ],
    ).order_by('created_at')[:limit]
    return [sync_polar_usage_entry(usage) for usage in pending]


def _record_orchestrator_usage(session, stopped_at, runtime_seconds=None):
    if runtime_seconds is not None:
        billed_minutes = _rounded_runtime_minutes_from_seconds(runtime_seconds, session.allocated_minutes)
        # Orchestrator runtime is floored to whole seconds. A ready session
        # with positive sub-second runtime still incurs the minimum charge.
        if billed_minutes == 0 and session.ready_at and stopped_at > session.ready_at:
            billed_minutes = session.rounded_runtime_minutes(stopped_at=stopped_at)
    elif session.ready_at:
        billed_minutes = session.rounded_runtime_minutes(stopped_at=stopped_at)
    else:
        billed_minutes = 0

    if billed_minutes <= 0:
        return None

    return _create_usage_entry(
        session,
        billed_minutes,
        {'stop_reason': session.stop_reason, 'source': 'orchestrator'},
    )


def process_orchestrator_event(session_id, payload):
    # Resolve ownership outside the write transaction so SQLite does not retain
    # a read lock while waiting for another callback/response writer.
    owner_id = ServerSession.objects.values_list('user_id', flat=True).get(pk=session_id)
    return _process_orchestrator_event(session_id, payload, owner_id)


@transaction.atomic
def _process_orchestrator_event(session_id, payload, owner_id):
    event_id, event_type = payload.get('event_id'), payload.get('event')
    supported = {'launch_accepted', 'ready', 'heartbeat', 'stopping', 'stopped', 'exited', 'killed', 'launch_failed'}
    if not event_id or event_type not in supported:
        raise SubscriptionError('Orchestrator events require an event_id and a supported event.')
    lock_user(owner_id)
    session = ServerSession.objects.select_for_update().get(pk=session_id)
    event, created = WebhookEvent.objects.get_or_create(
        provider='orchestrator', event_id=event_id,
        defaults={'event_type': event_type, 'payload': {**payload, 'website_session_id': str(session_id)}, 'processed_at': timezone.now()},
    )
    if not created:
        if str(event.payload.get('website_session_id', session_id)) != str(session_id):
            raise SubscriptionError('Event belongs to another session.')
        return event
    occurred_at = _parse_datetime(payload.get('occurred_at')) or timezone.now()
    terminal = event_type in {'stopped', 'exited', 'killed', 'launch_failed'}
    if session.status in TERMINAL_SESSION_STATUSES or (not terminal and session.last_event_at and occurred_at < session.last_event_at):
        event.status = WebhookEvent.STATUS_SKIPPED
        event.save(update_fields=['status'])
        return event
    if session.status == ServerSession.STATUS_STOPPING and not terminal:
        # A delayed heartbeat/ready can refresh liveness, never undo a stop.
        if event_type == 'heartbeat':
            session.last_heartbeat_at = max(session.last_heartbeat_at, occurred_at)
            session.save(update_fields=['last_heartbeat_at'])
        return event
    for key, field in [('orchestrator_session_id', 'orchestrator_session_id'), ('orchestrator_state', 'orchestrator_state'),
                       ('host', 'host'), ('port', 'port'), ('password', 'server_password')]:
        if payload.get(key) is not None:
            setattr(session, field, payload[key])
    if session.orchestrator_session_id:
        session.server_identifier = session.orchestrator_session_id
    if event_type == 'launch_accepted':
        if session.status == ServerSession.STATUS_PENDING:
            session.status = ServerSession.STATUS_LAUNCHING
    elif event_type == 'ready':
        session.status = ServerSession.STATUS_RUNNING
        session.ready_at = session.ready_at or _parse_datetime(payload.get('ready_at')) or occurred_at
        session.last_heartbeat_at = max(session.last_heartbeat_at, occurred_at)
    elif event_type == 'heartbeat':
        # Starting/stopping processes also send heartbeats; they are not ready.
        if payload.get('orchestrator_state') == 'running' or session.ready_at:
            session.status = ServerSession.STATUS_RUNNING
            session.ready_at = session.ready_at or _parse_datetime(payload.get('ready_at'))
        session.last_heartbeat_at = max(session.last_heartbeat_at, occurred_at)
    elif event_type == 'stopping':
        session.status = ServerSession.STATUS_STOPPING
        session.stop_reason = payload.get('reason') or 'stopping'
    elif terminal:
        session.status = ServerSession.STATUS_FAILED if event_type == 'launch_failed' else (
            ServerSession.STATUS_KILLED if event_type == 'killed' else ServerSession.STATUS_STOPPED)
        session.stopped_at = _parse_datetime(payload.get('stopped_at')) or occurred_at
        session.orchestrator_stopped_at = session.stopped_at
        session.stop_reason = payload.get('reason') or event_type
        session.launch_error_code = payload.get('error_code') or ''
        session.launch_error_message = payload.get('error_message') or ''
    session.last_event_at = max(session.last_event_at or occurred_at, occurred_at)
    session.save()
    if terminal and event_type != 'launch_failed':
        _record_orchestrator_usage(session, session.stopped_at, runtime_seconds=payload.get('runtime_seconds'))
    return event


def request_stop_server_session(session, reason='stopped', actor=None):
    session = ServerSession.objects.get(pk=session.pk)
    if session.status in TERMINAL_SESSION_STATUSES:
        return session
    if not session.orchestrator_session_id:
        raise SubscriptionError('The server launch is still being confirmed. Try again shortly.', status_code=409)
    try:
        orchestrator.stop_server(session.orchestrator_session_id, reason=reason,
                                 actor=actor or _actor_for_user(session.user))
    except orchestrator.OrchestratorError as exc:
        raise SubscriptionError(str(exc), status_code=503, code=exc.code) from exc
    # A callback may be writing the terminal state while this response arrives.
    # A single conditional write waits for SQLite's writer without attempting a
    # read-to-write transaction upgrade, and cannot overwrite a terminal state.
    ServerSession.objects.filter(pk=session.pk).exclude(
        status__in=TERMINAL_SESSION_STATUSES,
    ).update(status=ServerSession.STATUS_STOPPING, stop_reason=reason or 'stopping', updated_at=timezone.now())
    session.refresh_from_db()
    return session


def expire_stale_sessions(max_heartbeat_age_minutes=10):
    cutoff = timezone.now() - timedelta(minutes=max_heartbeat_age_minutes)
    stale_ids = list(ServerSession.objects.filter(
        status__in=OPEN_SESSION_STATUSES, last_heartbeat_at__lt=cutoff,
    ).values_list('pk', flat=True))
    expired = []
    for session_id in stale_ids:
        session = ServerSession.objects.get(pk=session_id)
        try:
            if session.orchestrator_session_id:
                details = orchestrator.get_server(session.orchestrator_session_id)
            else:
                matches = orchestrator.find_website_sessions(session.id)
                details = matches[0] if matches else None
        except orchestrator.OrchestratorError as exc:
            if exc.status_code != 404:
                # Network outage is not evidence of process death.
                continue
            details = None
        if details:
            state = details.get('state')
            stopped = state in {'stopped', 'exited', 'killed', 'failed'}
            process_orchestrator_event(session.id, {
                'event_id': f'reconcile:{session.id}:{details.get("id")}:{details.get("stoppedAt") or timezone.now().isoformat()}',
                'event': ('launch_failed' if state == 'failed' else 'stopped') if stopped else 'heartbeat',
                'occurred_at': details.get('stoppedAt') or timezone.now().isoformat(),
                'ready_at': details.get('readyAt'), 'stopped_at': details.get('stoppedAt'),
                'runtime_seconds': details.get('runtimeSeconds'),
                'orchestrator_session_id': details.get('id'), 'orchestrator_state': state,
                'reason': 'reconciled',
            })
            if not stopped:
                continue
        else:
            # The service is reachable and the old session no longer exists:
            # destructive restart. Charge only runtime last confirmed alive.
            with transaction.atomic():
                lock_user(session.user_id)
                session = ServerSession.objects.select_for_update().get(pk=session_id)
                if not session.is_open or session.last_heartbeat_at >= cutoff:
                    continue
                session.status = ServerSession.STATUS_EXPIRED
                session.stopped_at = min(session.last_heartbeat_at, timezone.now())
                session.stop_reason = 'orchestrator_session_lost'
                session.save()
                if session.ready_at:
                    _record_orchestrator_usage(session, session.stopped_at)
        expired.append(ServerSession.objects.get(pk=session_id))
    return expired


def validate_polar_webhook(secret, body, headers):
    try:
        return polar_gateway.validate_webhook(body, headers, secret)
    except polar_gateway.PolarGatewayError as exc:
        raise WebhookVerificationError(str(exc)) from exc


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
    if not created and event.status != WebhookEvent.STATUS_FAILED:
        return event

    try:
        if event_type.startswith('subscription.'):
            _upsert_entitlement_from_polar_subscription(data, event_id, payload.get('timestamp'))
            event.status = WebhookEvent.STATUS_PROCESSED
            event.error = ''
        else:
            event.status = WebhookEvent.STATUS_SKIPPED
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'error', 'processed_at'])
    except Exception as exc:
        event.status = WebhookEvent.STATUS_FAILED
        event.error = str(exc)
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'error', 'processed_at'])
        raise
    return event


def create_polar_checkout_url(user, plan, customer_ip_address=''):
    try:
        return polar_gateway.create_checkout_url(user, plan, customer_ip_address=customer_ip_address)
    except polar_gateway.PolarGatewayError as exc:
        raise SubscriptionError(str(exc)) from exc


@transaction.atomic
def _upsert_entitlement_from_polar_subscription(data, event_id, event_timestamp=None):
    user = _user_from_polar_data(data)
    plan = _plan_from_polar_data(data)
    if user is None or plan is None:
        raise SubscriptionError('Polar subscription webhook did not include a known user and plan.')

    subscription_id = str(data.get('id') or data.get('subscription_id') or '')
    if not subscription_id:
        raise SubscriptionError('Polar subscription webhook did not include a subscription ID.')

    lock_user(user.pk)
    incoming_at = _parse_dt(data.get('modified_at') or event_timestamp)
    previous = SubscriptionEntitlement.objects.filter(
        provider=SubscriptionEntitlement.PROVIDER_POLAR, provider_subscription_id=subscription_id,
    ).first()
    previous_at = _parse_dt((previous.metadata or {}).get('_event_at')) if previous else None
    if previous_at and (incoming_at is None or incoming_at <= previous_at):
        return
    data = {**data, '_event_at': incoming_at.isoformat() if incoming_at else None}

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
    status = POLAR_STATUS_MAP.get(raw_status, SubscriptionEntitlement.STATUS_INACTIVE)
    if status == SubscriptionEntitlement.STATUS_CANCELED and data.get('cancel_at_period_end') and period_end > timezone.now():
        status = SubscriptionEntitlement.STATUS_ACTIVE

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
    product_id = (
        data.get('product_id')
        or (data.get('product') or {}).get('id')
        or (data.get('products') or [{}])[0].get('id')
    )
    if product_id:
        plan = SubscriptionPlan.objects.filter(polar_product_id=product_id).first()
        return plan
    tier = (data.get('metadata') or {}).get('tier')
    if tier:
        return SubscriptionPlan.objects.filter(tier=tier).first()
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
