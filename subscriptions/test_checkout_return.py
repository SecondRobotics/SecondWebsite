import logging
from django.test import RequestFactory
from subscriptions.views import subscription_home
from SRCweb.log_filters import RedactCustomerSessionToken
from types import SimpleNamespace


def test_checkout_return_discards_customer_session_token():
    request = RequestFactory().get('/subscriptions/?customer_session_token=secret')
    request.user = SimpleNamespace(is_authenticated=True)
    response = subscription_home(request)
    assert response.status_code == 302
    assert response.url == '/subscriptions/'


def test_access_log_redacts_formatted_customer_session_token():
    record = logging.LogRecord('django.server', logging.INFO, '', 0,
                               '"GET %s HTTP/1.1" %s',
                               ('/subscriptions/?customer_session_token=secret&other=value', 302), None)
    assert RedactCustomerSessionToken().filter(record)
    assert record.getMessage() == '"GET /subscriptions/?customer_session_token=[REDACTED]&other=value HTTP/1.1" 302'
