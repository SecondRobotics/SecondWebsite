import requests
from django.conf import settings


class OrchestratorError(ValueError):
    def __init__(self, message, status_code=None, code='ORCHESTRATOR_ERROR', payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.payload = payload or {}


def is_configured():
    return bool(getattr(settings, 'ORCHESTRATOR_API_BASE_URL', '') and getattr(settings, 'ORCHESTRATOR_API_TOKEN', ''))


def _base_url():
    return getattr(settings, 'ORCHESTRATOR_API_BASE_URL', '').rstrip('/')


def _timeout():
    return float(getattr(settings, 'ORCHESTRATOR_REQUEST_TIMEOUT_SECONDS', 10))


def _request(method, path, **kwargs):
    if not is_configured():
        raise OrchestratorError('The server orchestrator is not configured.', code='ORCHESTRATOR_NOT_CONFIGURED')

    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {settings.ORCHESTRATOR_API_TOKEN}'
    headers.setdefault('Accept', 'application/json')
    if 'json' in kwargs:
        headers.setdefault('Content-Type', 'application/json')

    try:
        response = requests.request(
            method,
            f'{_base_url()}{path}',
            headers=headers,
            timeout=_timeout(),
            **kwargs,
        )
    except requests.RequestException as exc:
        raise OrchestratorError('The server orchestrator could not be reached.', code='ORCHESTRATOR_UNAVAILABLE') from exc

    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {}

    if response.status_code >= 400:
        error = payload.get('error') if isinstance(payload, dict) else None
        message = (error or {}).get('message') or 'The server orchestrator rejected the request.'
        code = (error or {}).get('code') or 'ORCHESTRATOR_REJECTED_REQUEST'
        raise OrchestratorError(message, status_code=response.status_code, code=code, payload=payload)

    return payload


def get_casual_games():
    payload = _request('GET', '/v1/games', params={'kind': 'casual'})
    return payload.get('games', [])


def launch_casual(session, *, game_code, comment, password='', launch_source='website', actor=None):
    payload = {
        'kind': 'casual',
        'gameCode': str(game_code),
        'websiteServerSessionId': str(session.id),
        'requestedMinutes': session.requested_minutes,
        'maxMinutes': session.allocated_minutes,
        'comment': comment,
        'launchSource': launch_source,
    }
    if password:
        payload['password'] = password
    if actor:
        payload['actor'] = actor

    return _request('POST', '/v1/servers', json=payload)


def stop_server(orchestrator_session_id, *, reason='website_stop', actor=None):
    payload = {'reason': reason}
    if actor:
        payload['actor'] = actor
    return _request('POST', f'/v1/servers/{orchestrator_session_id}/stop', json=payload)
