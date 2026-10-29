from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from subscriptions.models import ServerSession, SubscriptionEntitlement, SubscriptionPlan, UsageLedgerEntry, WebhookEvent
from subscriptions.services import (
    SubscriptionError, _record_launch_response, available_credits, expire_stale_sessions,
    launch_casual_server, process_orchestrator_event, process_polar_webhook,
    request_stop_server_session, start_server_session, stop_server_session,
)
from subscriptions.tests import create_user, create_entitlement
from subscriptions.polar_gateway import PolarGatewayError
from subscriptions.orchestrator import OrchestratorError


@override_settings(POLAR_CASUAL_SERVER_METER_ID='dedicated-meter')
class LaunchReadinessTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.entitlement = create_entitlement(self.user)

    def callback(self, session, event, **details):
        return process_orchestrator_event(session.id, {
            'event_id': f'{event}-{WebhookEvent.objects.count()}', 'event': event, **details,
        })

    @patch('subscriptions.polar_gateway.get_customer_meter')
    @patch('subscriptions.polar_gateway.ingest_usage_event')
    def test_usage_hold_survives_failure_ingestion_delay_and_portal_credit_grants(self, ingest, meter):
        self.entitlement.provider = SubscriptionEntitlement.PROVIDER_POLAR
        self.entitlement.save()
        meter.return_value = SimpleNamespace(balance=60, consumed_units=100)
        session = start_server_session(self.user, 60)
        session.started_at = timezone.now() - timedelta(minutes=60)
        session.save()
        stop_server_session(session)
        ingest.assert_not_called()  # Network work is outside lifecycle transactions.
        self.assertEqual(available_credits(self.entitlement), 0)
        ingest.side_effect = PolarGatewayError('offline')
        call_command('sync_polar_usage')
        self.assertEqual(available_credits(self.entitlement), 0)
        ingest.side_effect = None
        ingest.return_value = SimpleNamespace(inserted=1, duplicates=0)
        call_command('sync_polar_usage')
        self.assertEqual(available_credits(self.entitlement), 0)  # accepted, not aggregated
        meter.return_value = SimpleNamespace(balance=0, consumed_units=160)
        self.assertEqual(available_credits(self.entitlement), 0)  # reflected exactly once
        meter.return_value = SimpleNamespace(balance=90, consumed_units=160)
        self.assertEqual(available_credits(self.entitlement), 90)  # portal grants remain authoritative
        self.assertEqual(UsageLedgerEntry.objects.count(), 1)

    def test_terminal_state_survives_reordered_callbacks_and_launch_response(self):
        session = start_server_session(self.user, 30)
        self.callback(session, 'stopped', runtime_seconds=61)
        self.callback(session, 'ready', occurred_at=(timezone.now() - timedelta(minutes=2)).isoformat())
        _record_launch_response(session.pk, {'id': 'orchestrator', 'state': 'starting'})
        session.refresh_from_db()
        self.assertEqual(session.status, ServerSession.STATUS_STOPPED)
        self.assertEqual(UsageLedgerEntry.objects.get().credits, 5)

    def test_heartbeat_does_not_reverse_stop_or_make_starting_ready(self):
        session = start_server_session(self.user, 30, status=ServerSession.STATUS_LAUNCHING)
        self.callback(session, 'heartbeat', orchestrator_state='starting')
        session.refresh_from_db()
        self.assertEqual(session.status, ServerSession.STATUS_LAUNCHING)
        self.callback(session, 'stopping')
        self.callback(session, 'heartbeat', orchestrator_state='running')
        session.refresh_from_db()
        self.assertEqual(session.status, ServerSession.STATUS_STOPPING)

    @patch('subscriptions.orchestrator.stop_server')
    def test_stop_supplies_actor_and_does_not_overwrite_terminal_callback(self, stop):
        session = start_server_session(self.user, 30)
        session.orchestrator_session_id = 'orch'
        session.save()
        stop.side_effect = lambda *a, **kw: self.callback(session, 'stopped', runtime_seconds=61)
        result = request_stop_server_session(session)
        self.assertEqual(result.status, ServerSession.STATUS_STOPPED)
        self.assertEqual(stop.call_args.kwargs['actor']['type'], 'website_user')

    @patch('subscriptions.orchestrator.launch_casual')
    def test_discord_launch_actor_and_ready_race(self, launch):
        def accepted(session, **kwargs):
            self.callback(session, 'ready', orchestrator_session_id='orch')
            return {'id': 'orch', 'state': 'starting', 'port': 11115}
        launch.side_effect = accepted
        session = launch_casual_server(self.user, 30, game_code='20', launch_source='discord_bot')
        self.assertEqual(launch.call_args.kwargs['actor']['type'], 'discord_user')
        self.assertEqual(session.status, ServerSession.STATUS_RUNNING)

    @patch('subscriptions.orchestrator.launch_casual', side_effect=OrchestratorError('timeout'))
    def test_uncertain_launch_retains_reservation(self, launch):
        with self.assertRaises(SubscriptionError):
            launch_casual_server(self.user, 30, game_code='20')
        self.assertEqual(ServerSession.objects.get().status, ServerSession.STATUS_PENDING)

    @patch('subscriptions.orchestrator.get_server')
    def test_cleanup_reconciles_all_open_states_and_uses_last_confirmed_runtime(self, get):
        get.side_effect = OrchestratorError('missing', status_code=404)
        for status in ['pending', 'launching', 'running', 'stopping']:
            session = start_server_session(self.user, 60, status=status)
            session.orchestrator_session_id = 'old'
            session.started_at = timezone.now() - timedelta(minutes=60)
            session.ready_at = session.started_at if status in ['running', 'stopping'] else None
            session.last_heartbeat_at = session.started_at + timedelta(minutes=6)
            session.save()
            self.assertEqual(len(expire_stale_sessions()), 1)
            session.refresh_from_db()
            self.assertEqual(session.status, 'expired')
            if session.ready_at:
                self.assertEqual(session.usage_entry.credits, 10)
            else:
                self.assertFalse(UsageLedgerEntry.objects.filter(server_session=session).exists())

    @patch('subscriptions.orchestrator.get_server', side_effect=OrchestratorError('offline'))
    def test_cleanup_does_not_infer_process_death_from_network_failure(self, get):
        session = start_server_session(self.user, 30)
        session.orchestrator_session_id = 'orch'
        session.last_heartbeat_at = timezone.now() - timedelta(days=1)
        session.save()
        self.assertEqual(expire_stale_sessions(), [])
        self.assertFalse(UsageLedgerEntry.objects.exists())

    def test_webhook_failure_is_retryable_and_old_updates_do_not_regress_entitlement(self):
        now = timezone.now()
        payload = {'type': 'subscription.updated', 'timestamp': now.isoformat(), 'data': {
            'id': 'sub-test', 'status': 'active', 'customer': {'external_id': str(self.user.pk)},
            'product_id': 'unmapped',
        }}
        with self.assertRaises(SubscriptionError):
            process_polar_webhook(payload, 'polar-retry')
        plan = SubscriptionPlan.objects.get(tier='supporter')
        plan.polar_product_id = 'unmapped'
        plan.save()
        self.assertEqual(process_polar_webhook(payload, 'polar-retry').status, 'processed')
        older = {**payload, 'timestamp': (now - timedelta(days=1)).isoformat(),
                 'data': {**payload['data'], 'status': 'revoked'}}
        process_polar_webhook(older, 'old-event')
        entitlement = SubscriptionEntitlement.objects.get(provider_subscription_id='sub-test')
        self.assertEqual(entitlement.status, 'active')

    def test_usage_keeps_reserved_billing_period_after_entitlement_renews(self):
        session = start_server_session(self.user, 30)
        period = session.billing_period_start
        self.entitlement.current_period_start += timedelta(days=30)
        self.entitlement.current_period_end += timedelta(days=30)
        self.entitlement.save()
        stop_server_session(session)
        self.assertEqual(session.usage_entry.billing_period_start, period)

    def test_session_reservation_cannot_cross_billing_cycle(self):
        self.entitlement.current_period_end = timezone.now() + timedelta(minutes=12)
        self.entitlement.save()
        session = start_server_session(self.user, 120)
        self.assertLessEqual(session.allocated_minutes, 11)
