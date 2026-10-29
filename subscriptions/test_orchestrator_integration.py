"""Run with ORCHESTRATOR_REPO=/path/to/built/orchestrator; no external services."""
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time
from unittest import skipUnless

from django.test import LiveServerTestCase, override_settings
from rest_framework.test import APIClient

from subscriptions.models import ServerSession, SubscriptionPlan, UsageLedgerEntry
from subscriptions.tests import create_user, create_entitlement


@skipUnless(os.environ.get('ORCHESTRATOR_REPO'), 'Set ORCHESTRATOR_REPO for the cross-service test.')
class OrchestratorIntegrationTests(LiveServerTestCase):
    def test_discord_and_browser_launch_callbacks_and_stop_use_real_contracts(self):
        repo = Path(os.environ['ORCHESTRATOR_REPO']).resolve()
        with tempfile.TemporaryDirectory(prefix='second-contract-') as runtime:
            script = """
import Fastify from 'fastify';
import app from './dist/app.js';
const server = Fastify();
await server.register(app);
await server.listen({ host: '127.0.0.1', port: 0 });
console.log(JSON.stringify({ url: server.listeningOrigin }));
process.on('SIGTERM', async () => { await server.close(); process.exit(0); });
"""
            env = {key: value for key, value in os.environ.items() if key in ['PATH', 'HOME', 'TMPDIR']}
            env.update({
                'XRC_PROCESS_MODE': 'fake', 'NODE_ENV': 'test', 'API_KEY': 'integration-key',
                'SERVICE_TOKENS': 'integration-token:servers:casual:create,servers:read,servers:stop',
                'SECONDWEBSITE_BASE_URL': self.live_server_url,
                'SECONDWEBSITE_CALLBACK_RETRY_BASE_MS': '10',
                'SERVER_LOG_DIR': runtime + '/logs', 'CHAT_LOG_DIR': runtime + '/chat',
                'SCORE_DATA_DIR': runtime + '/scores', 'EVENT_LOG_DIR': runtime + '/events',
            })
            child = subprocess.Popen(['node', '--input-type=module', '-e', script], cwd=repo,
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(select.select([child.stdout], [], [], 15)[0], 'Orchestrator startup timed out')
                line = child.stdout.readline()
                self.assertTrue(line, 'Orchestrator did not start')
                url = json.loads(line)['url']
                with override_settings(ORCHESTRATOR_API_BASE_URL=url, ORCHESTRATOR_API_TOKEN='integration-token',
                                       API_KEY='integration-key', ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver']):
                    # TestCase data migrations are flushed by LiveServerTestCase.
                    SubscriptionPlan.objects.get_or_create(tier='supporter', defaults={
                        'name': 'Supporter', 'monthly_price_usd': 5, 'monthly_credits': 360,
                        'max_session_minutes': 120,
                    })
                    user = create_user()
                    create_entitlement(user)
                    client = APIClient()
                    for source, game in [('discord_bot', '23'), ('website', '24')]:
                        if source == 'website':
                            client.force_authenticate(user)
                        response = client.post('/api/subscriptions/server-sessions/start/', {
                            'owner_discord_id': str(user.pk), 'game_code': game,
                            'requested_minutes': 5, 'launch_source': source,
                        }, format='json', HTTP_X_API_KEY='integration-key' if source == 'discord_bot' else '')
                        self.assertEqual(response.status_code, 201, response.data)
                        session_id = response.data['session']['id']
                        self.wait_for_status(session_id, 'running')
                        time.sleep(1.1)  # One runtime second rounds to five credits.
                        response = client.post(f'/api/subscriptions/server-sessions/{session_id}/stop/', {},
                                               format='json', HTTP_X_API_KEY='integration-key' if source == 'discord_bot' else '')
                        self.assertEqual(response.status_code, 200, response.data)
                        self.wait_for_status(session_id, 'stopped')
                        usage = UsageLedgerEntry.objects.get(server_session_id=session_id)
                        self.assertEqual(usage.credits, 5)
                    self.assertEqual(UsageLedgerEntry.objects.count(), 2)
            finally:
                child.terminate()
                try:
                    child.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.communicate()

    def wait_for_status(self, session_id, status):
        for _ in range(100):
            if ServerSession.objects.get(pk=session_id).status == status:
                return
            time.sleep(0.05)
        self.fail(f'Session did not become {status}')

    def test_stop_response_waits_for_sqlite_callback_writer(self):
        self.assert_response_waits_for_sqlite_callback_writer('stop')

    def test_launch_response_waits_for_sqlite_callback_writer(self):
        self.assert_response_waits_for_sqlite_callback_writer('launch')

    def assert_response_waits_for_sqlite_callback_writer(self, response_kind):
        import threading
        from unittest.mock import patch
        from django.db import close_old_connections, connection, transaction
        from django.utils import timezone
        from subscriptions.services import request_stop_server_session, _record_launch_response

        if connection.vendor != 'sqlite':
            self.skipTest('Exercises SQLite read-to-write lock upgrades.')
        SubscriptionPlan.objects.get_or_create(tier='supporter', defaults={
            'name': 'Supporter', 'monthly_price_usd': 5, 'monthly_credits': 360,
            'max_session_minutes': 120,
        })
        user = create_user()
        entitlement = create_entitlement(user)
        session = ServerSession.objects.create(
            user=user, entitlement=entitlement, requested_minutes=5, allocated_minutes=5,
            status='running', orchestrator_session_id='stop-race',
        )
        writer_locked = threading.Event()
        errors = []

        def callback_writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    ServerSession.objects.filter(pk=session.pk).update(
                        status='stopped', stop_reason='callback', stopped_at=timezone.now(),
                    )
                    writer_locked.set()
                    time.sleep(0.15)
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        writer = threading.Thread(target=callback_writer)

        def stop_response(*args, **kwargs):
            writer.start()
            self.assertTrue(writer_locked.wait(5), 'Callback writer did not start')

        try:
            if response_kind == 'stop':
                with patch('subscriptions.orchestrator.stop_server', side_effect=stop_response):
                    result = request_stop_server_session(session)
            else:
                stop_response()
                result = _record_launch_response(session.pk, {}, user.pk)
            self.assertEqual(result.status, 'stopped')
            self.assertEqual(result.stop_reason, 'callback')
        finally:
            writer.join(5)
        self.assertFalse(writer.is_alive())
        self.assertEqual(errors, [])
