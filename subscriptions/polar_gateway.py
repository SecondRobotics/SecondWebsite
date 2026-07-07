from django.conf import settings

from polar_sdk import Polar
from polar_sdk.webhooks import validate_event


class PolarGatewayError(ValueError):
    pass


def _timeout_ms():
    return int(float(getattr(settings, 'POLAR_REQUEST_TIMEOUT_SECONDS', 10)) * 1000)


def _client():
    token = getattr(settings, 'POLAR_ACCESS_TOKEN', '')
    if not token:
        raise PolarGatewayError('Polar access token is not configured.')

    kwargs = {
        'access_token': token,
        'timeout_ms': _timeout_ms(),
    }
    server_url = getattr(settings, 'POLAR_API_BASE_URL', '')
    if server_url:
        kwargs['server_url'] = server_url
    else:
        kwargs['server'] = getattr(settings, 'POLAR_SERVER', 'production') or 'production'
    return Polar(**kwargs)


def create_checkout_url(user, plan, customer_ip_address=''):
    if not plan.polar_product_id:
        raise PolarGatewayError(f'Polar product ID is not configured for {plan.name}.')

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

    try:
        checkout = _client().checkouts.create(request=payload)
    except Exception as exc:
        raise PolarGatewayError('Polar checkout could not be created.') from exc

    checkout_url = getattr(checkout, 'url', '')
    if not checkout_url:
        raise PolarGatewayError('Polar checkout response did not include a checkout URL.')
    return checkout_url


def get_customer_credit_balance(user):
    meter_id = getattr(settings, 'POLAR_CASUAL_SERVER_METER_ID', '')
    if not meter_id:
        raise PolarGatewayError('Polar casual server meter ID is not configured.')

    try:
        response = _client().customer_meters.list(
            external_customer_id=str(user.id),
            meter_id=meter_id,
            limit=1,
        )
    except Exception as exc:
        raise PolarGatewayError('Polar credit balance could not be loaded.') from exc

    result = getattr(response, 'result', None)
    items = getattr(result, 'items', None) or []
    if not items:
        raise PolarGatewayError('Polar credit balance is not available for this customer yet.')
    return int(getattr(items[0], 'balance', 0))


def ingest_usage_event(session, credits, occurred_at):
    event_name = getattr(settings, 'POLAR_CASUAL_SERVER_EVENT_NAME', '') or 'casual_server_credits'
    try:
        return _client().events.ingest(request={
            'events': [{
                'name': event_name,
                'external_customer_id': str(session.user.id),
                'external_id': f'casual-server-session:{session.id}',
                'timestamp': occurred_at,
                'metadata': {
                    'credits': credits,
                    'minutes': credits,
                    'server_session_id': str(session.id),
                    'orchestrator_session_id': session.orchestrator_session_id,
                    'game_code': session.game_code,
                    'stop_reason': session.stop_reason,
                },
            }],
        })
    except Exception as exc:
        raise PolarGatewayError('Polar usage event could not be ingested.') from exc


def validate_webhook(body, headers, secret):
    if not secret:
        raise PolarGatewayError('Polar webhook secret is not configured.')
    try:
        event = validate_event(body, headers, secret)
    except Exception as exc:
        raise PolarGatewayError('Invalid Polar webhook signature.') from exc
    if hasattr(event, 'model_dump'):
        return event.model_dump(mode='json')
    return dict(event)
