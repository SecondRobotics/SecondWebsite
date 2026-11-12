"""Keep Polar's short-lived portal credential out of application access logs."""
import logging
import re


class RedactCustomerSessionToken(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        redacted = re.sub(
            r'(customer_session_token=)[^&\s\"\x27]+',
            r'\1[REDACTED]', message, flags=re.IGNORECASE,
        )
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
