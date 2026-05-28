import base64
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from discordoauth2.models import User
from subscriptions.models import ServerSession, SubscriptionEntitlement, SubscriptionPlan, UsageLedgerEntry, WebhookEvent
from subscriptions.services import (
    SubscriptionError,
    expire_stale_sessions,
    process_orchestrator_event,
    start_server_session,
    stop_server_session,
    verify_standard_webhook_signature,
)


class MockResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = json.dumps(self._payload).encode('utf-8')

    def json(self):
        return self._payload


def create_user(user_id=1001):
    return User.objects.create(
        id=user_id,
        username=f'user{user_id}',
        discriminator='0001',
        avatar='https://cdn.discordapp.com/embed/avatars/0.png',
        public_flags=0,
        flags=0,
        locale='en-US',
        mfa_enabled=False,
        email=f'user{user_id}@example.com',
        verified=True,
    )


def create_entitlement(user, tier='supporter', minutes=360):
    plan = SubscriptionPlan.objects.get(tier=tier)
    if minutes != plan.monthly_server_minutes:
        plan.monthly_server_minutes = minutes
        plan.save(update_fields=['monthly_server_minutes'])
    now = timezone.now()
    return SubscriptionEntitlement.objects.create(
        user=user,
        plan=plan,
        provider=SubscriptionEntitlement.PROVIDER_COMP,
        provider_subscription_id=f'comp-{user.id}-{tier}',
        status=SubscriptionEntitlement.STATUS_ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )


class SubscriptionServiceTests(TestCase):
    def test_start_requires_active_entitlement(self):
        user = create_user()

        with self.assertRaises(SubscriptionError):
            start_server_session(user)

    def test_start_limits_session_to_plan_and_remaining_minutes(self):
        user = create_user()
        create_entitlement(user, tier='supporter', minutes=30)

        session = start_server_session(user, requested_minutes=240, game='xRC')

        self.assertEqual(session.allocated_minutes, 30)
        self.assertEqual(session.requested_minutes, 240)
        self.assertEqual(session.game, 'xRC')

    def test_cannot_start_concurrent_session(self):
        user = create_user()
        create_entitlement(user)
        start_server_session(user)

        with self.assertRaises(SubscriptionError):
            start_server_session(user)

    def test_plan_can_allow_multiple_concurrent_sessions(self):
        user = create_user()
        plan = SubscriptionPlan.objects.get(tier='supporter')
        plan.max_concurrent_servers = 2
        plan.monthly_server_minutes = 360
        plan.save(update_fields=['max_concurrent_servers', 'monthly_server_minutes'])
        create_entitlement(user)

        start_server_session(user, requested_minutes=30)
        second = start_server_session(user, requested_minutes=30)

        self.assertEqual(second.allocated_minutes, 30)

    def test_highest_priority_entitlement_is_used(self):
        user = create_user()
        supporter = SubscriptionPlan.objects.get(tier='supporter')
        host = SubscriptionPlan.objects.get(tier='host')
        supporter.entitlement_priority = 100
        supporter.monthly_server_minutes = 30
        supporter.save(update_fields=['entitlement_priority', 'monthly_server_minutes'])
        host.entitlement_priority = 10
        host.monthly_server_minutes = 1500
        host.save(update_fields=['entitlement_priority', 'monthly_server_minutes'])
        create_entitlement(user, tier='host')
        create_entitlement(user, tier='supporter', minutes=30)

        session = start_server_session(user, requested_minutes=240)

        self.assertEqual(session.entitlement.plan.tier, 'supporter')
        self.assertEqual(session.allocated_minutes, 30)

    def test_stop_records_rounded_usage_once(self):
        user = create_user()
        create_entitlement(user)
        session = start_server_session(user)
        session.started_at = timezone.now() - timedelta(minutes=6)
        session.save(update_fields=['started_at'])

        stop_server_session(session)
        stop_server_session(session)

        usage = UsageLedgerEntry.objects.get(server_session=session)
        self.assertEqual(usage.minutes, 10)
        self.assertEqual(UsageLedgerEntry.objects.count(), 1)

    def test_exhausted_entitlement_rejects_start(self):
        user = create_user()
        entitlement = create_entitlement(user, minutes=30)
        UsageLedgerEntry.objects.create(
            user=user,
            entitlement=entitlement,
            billing_period_start=entitlement.current_period_start,
            billing_period_end=entitlement.current_period_end,
            minutes=30,
            reason=UsageLedgerEntry.REASON_ADMIN_ADJUSTMENT,
        )

        with self.assertRaises(SubscriptionError):
            start_server_session(user)

    def test_expire_stale_sessions_marks_expired_and_records_usage(self):
        user = create_user()
        create_entitlement(user)
        session = start_server_session(user)
        session.started_at = timezone.now() - timedelta(minutes=16)
        session.last_heartbeat_at = timezone.now() - timedelta(minutes=12)
        session.save(update_fields=['started_at', 'last_heartbeat_at'])

        expired = expire_stale_sessions(max_heartbeat_age_minutes=10)

        self.assertEqual(len(expired), 1)
        session.refresh_from_db()
        self.assertEqual(session.status, ServerSession.STATUS_EXPIRED)
        self.assertEqual(UsageLedgerEntry.objects.get(server_session=session).minutes, 20)

    def test_orchestrator_ready_and_stopped_events_record_usage_once(self):
        user = create_user()
        create_entitlement(user)
        session = start_server_session(user, requested_minutes=60, status=ServerSession.STATUS_LAUNCHING)
        ready_at = timezone.now() - timedelta(minutes=7)

        process_orchestrator_event(str(session.id), {
            'event_id': 'evt-ready',
            'event': 'ready',
            'occurred_at': ready_at.isoformat(),
            'orchestrator_session_id': 'orch-1',
            'orchestrator_state': 'running',
            'host': 'play.example.test',
            'port': 11115,
            'password': 'secret',
            'ready_at': ready_at.isoformat(),
        })
        process_orchestrator_event(str(session.id), {
            'event_id': 'evt-stopped',
            'event': 'stopped',
            'occurred_at': timezone.now().isoformat(),
            'orchestrator_session_id': 'orch-1',
            'orchestrator_state': 'stopped',
            'runtime_seconds': 370,
            'reason': 'user_stop',
        })
        process_orchestrator_event(str(session.id), {
            'event_id': 'evt-stopped',
            'event': 'stopped',
            'occurred_at': timezone.now().isoformat(),
            'orchestrator_session_id': 'orch-1',
            'orchestrator_state': 'stopped',
            'runtime_seconds': 370,
            'reason': 'user_stop',
        })

        session.refresh_from_db()
        self.assertEqual(session.status, ServerSession.STATUS_STOPPED)
        self.assertEqual(session.host, 'play.example.test')
        self.assertEqual(session.port, 11115)
        self.assertEqual(session.server_password, 'secret')
        self.assertEqual(UsageLedgerEntry.objects.get(server_session=session).minutes, 10)
        self.assertEqual(WebhookEvent.objects.filter(provider='orchestrator').count(), 2)

    def test_orchestrator_launch_failed_does_not_record_usage(self):
        user = create_user()
        create_entitlement(user)
        session = start_server_session(user, requested_minutes=60, status=ServerSession.STATUS_LAUNCHING)

        process_orchestrator_event(str(session.id), {
            'event_id': 'evt-failed',
            'event': 'launch_failed',
            'occurred_at': timezone.now().isoformat(),
            'orchestrator_session_id': 'orch-1',
            'orchestrator_state': 'failed',
            'error_code': 'LAUNCH_FAILED',
            'error_message': 'Process exited during startup.',
        })

        session.refresh_from_db()
        self.assertEqual(session.status, ServerSession.STATUS_FAILED)
        self.assertEqual(session.launch_error_code, 'LAUNCH_FAILED')
        self.assertEqual(UsageLedgerEntry.objects.count(), 0)


class SubscriptionApiTests(TestCase):
    def test_entitlement_endpoint_requires_authentication(self):
        response = APIClient().get('/api/subscriptions/me/entitlement/')

        self.assertEqual(response.status_code, 401)

    @override_settings(ORCHESTRATOR_API_BASE_URL='https://orchestrator.example.test', ORCHESTRATOR_API_TOKEN='orch-token')
    @patch('subscriptions.orchestrator.requests.request')
    def test_user_token_can_launch_and_request_stop(self, mock_request):
        mock_request.side_effect = [
            MockResponse(payload={
                'id': 'orch-1',
                'state': 'starting',
                'host': 'play.example.test',
                'port': 11115,
                'password': 'generated',
            }),
            MockResponse(payload={'success': True}),
        ]
        user = create_user()
        create_entitlement(user, tier='host')
        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.post('/api/subscriptions/server-sessions/start/', {
            'requested_minutes': 60,
            'game_code': '20',
            'game': 'Push Back',
            'comment': 'CasualPB',
            'launch_context': {'source': 'discord_bot'},
        }, format='json')
        self.assertEqual(response.status_code, 201)
        session_id = response.data['session']['id']
        self.assertEqual(response.data['session']['status'], ServerSession.STATUS_LAUNCHING)
        self.assertEqual(response.data['session']['password'], 'generated')

        response = client.post(f'/api/subscriptions/server-sessions/{session_id}/stop/', {
            'reason': 'bot_stop',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServerSession.objects.get(id=session_id).status, ServerSession.STATUS_STOPPING)
        self.assertEqual(UsageLedgerEntry.objects.count(), 0)

    @override_settings(
        ORCHESTRATOR_API_BASE_URL='https://orchestrator.example.test',
        ORCHESTRATOR_API_TOKEN='orch-token',
        API_KEY='service-api-key',
    )
    @patch('subscriptions.orchestrator.requests.request')
    def test_api_key_can_launch_for_discord_user(self, mock_request):
        mock_request.return_value = MockResponse(payload={'id': 'orch-1', 'state': 'starting'})
        owner = create_user(2002)
        create_entitlement(owner, tier='host')
        client = APIClient()
        client.credentials(HTTP_X_API_KEY='service-api-key')

        response = client.post('/api/subscriptions/server-sessions/start/', {
            'owner_discord_id': str(owner.id),
            'requested_minutes': 30,
            'game_code': '20',
            'comment': 'CasualPB',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        session = ServerSession.objects.get(id=response.data['session']['id'])
        self.assertEqual(session.user, owner)
        self.assertEqual(session.status, ServerSession.STATUS_LAUNCHING)

    @override_settings(API_KEY='service-api-key')
    def test_api_key_can_read_user_entitlement(self):
        owner = create_user(2005)
        create_entitlement(owner, tier='host')
        client = APIClient()
        client.credentials(HTTP_X_API_KEY='service-api-key')

        response = client.get(f'/api/subscriptions/users/{owner.id}/entitlement/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['discord_user_id'], str(owner.id))
        self.assertTrue(response.data['entitlement']['active'])

    @override_settings(API_KEY='service-api-key')
    def test_orchestrator_callback_requires_api_key(self):
        owner = create_user(3003)
        create_entitlement(owner)
        session = start_server_session(owner, status=ServerSession.STATUS_LAUNCHING)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY='wrong-key')

        response = client.post(f'/api/subscriptions/server-sessions/{session.id}/orchestrator-event/', {
            'event_id': 'evt-ready',
            'event': 'ready',
            'occurred_at': timezone.now().isoformat(),
            'orchestrator_session_id': 'orch-1',
            'orchestrator_state': 'running',
        }, format='json')

        self.assertEqual(response.status_code, 401)

    @override_settings(API_KEY='service-api-key')
    def test_orchestrator_callback_accepts_api_key(self):
        owner = create_user(3005)
        create_entitlement(owner)
        session = start_server_session(owner, status=ServerSession.STATUS_LAUNCHING)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY='service-api-key')

        response = client.post(f'/api/subscriptions/server-sessions/{session.id}/orchestrator-event/', {
            'event_id': 'evt-ready',
            'event': 'ready',
            'occurred_at': timezone.now().isoformat(),
            'orchestrator_session_id': 'orch-1',
            'orchestrator_state': 'running',
        }, format='json')

        self.assertEqual(response.status_code, 200)


class PolarWebhookTests(TestCase):
    @override_settings(POLAR_WEBHOOK_SECRET='whsec_' + base64.b64encode(b'secret').decode('utf-8'))
    def test_standard_webhook_signature_verification_accepts_valid_signature(self):
        body = b'{"type":"subscription.updated"}'
        webhook_id = 'evt_123'
        timestamp = str(int(timezone.now().timestamp()))
        signed = b'.'.join([webhook_id.encode(), timestamp.encode(), body])
        signature = 'v1,' + base64.b64encode(hmac.new(b'secret', signed, hashlib.sha256).digest()).decode('utf-8')

        verify_standard_webhook_signature(
            'whsec_' + base64.b64encode(b'secret').decode('utf-8'),
            body,
            webhook_id,
            timestamp,
            signature,
        )

    @override_settings(POLAR_WEBHOOK_SECRET='plain-secret')
    def test_polar_subscription_webhook_upserts_entitlement_and_is_idempotent(self):
        user = create_user()
        plan = SubscriptionPlan.objects.get(tier='supporter')
        plan.polar_product_id = 'prod_supporter'
        plan.save(update_fields=['polar_product_id'])
        body = {
            'type': 'subscription.updated',
            'data': {
                'id': 'sub_123',
                'status': 'active',
                'current_period_start': timezone.now().isoformat(),
                'current_period_end': (timezone.now() + timedelta(days=30)).isoformat(),
                'customer': {'id': 'cus_123', 'external_id': str(user.id)},
                'product_id': 'prod_supporter',
            },
        }
        raw_body = json.dumps(body).encode('utf-8')
        webhook_id = 'evt_123'
        timestamp = str(int(timezone.now().timestamp()))
        signed = b'.'.join([webhook_id.encode(), timestamp.encode(), raw_body])
        signature = 'v1,' + base64.b64encode(hmac.new(b'plain-secret', signed, hashlib.sha256).digest()).decode('utf-8')

        client = APIClient()
        response = client.post(
            '/subscriptions/polar/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_WEBHOOK_ID=webhook_id,
            HTTP_WEBHOOK_TIMESTAMP=timestamp,
            HTTP_WEBHOOK_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)

        response = client.post(
            '/subscriptions/polar/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_WEBHOOK_ID=webhook_id,
            HTTP_WEBHOOK_TIMESTAMP=timestamp,
            HTTP_WEBHOOK_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)

        entitlement = SubscriptionEntitlement.objects.get(provider_subscription_id='sub_123')
        self.assertEqual(entitlement.user, user)
        self.assertEqual(entitlement.plan.tier, 'supporter')
        self.assertEqual(WebhookEvent.objects.count(), 1)
