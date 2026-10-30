from decimal import Decimal, ROUND_FLOOR

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum

from discordoauth2.models import User
from . import polar_gateway
from .models import PolarCreditAccount, SubscriptionEntitlement, UsageLedgerEntry


def lock_user(user_id):
    # A real write also serializes reservations on SQLite, where FOR UPDATE is
    # ignored. Take this lock before reading entitlement, meter, or ledger state.
    User.objects.filter(pk=user_id).update(last_login=F('last_login'))


@transaction.atomic
def spendable_polar_balance(user):
    lock_user(user.pk)
    meter = polar_gateway.get_customer_meter(user)
    meter_id = str(getattr(settings, 'POLAR_CASUAL_SERVER_METER_ID', ''))
    consumed = Decimal(str(meter.consumed_units))
    total = UsageLedgerEntry.objects.filter(
        user=user, entitlement__provider=SubscriptionEntitlement.PROVIDER_POLAR,
        metadata__polar_meter_id=meter_id,
    ).aggregate(total=Sum('credits'))['total'] or 0
    account, created = PolarCreditAccount.objects.select_for_update().get_or_create(
        user=user, meter_id=meter_id,
        defaults={'observed_consumed_units': consumed},
    )
    new_usage = max(total - account.local_credits_seen, 0)
    # A reset of consumed_units is not proof that pending usage was processed.
    reflected = max(consumed - account.observed_consumed_units, Decimal(0)) if not created else Decimal(0)
    account.unreflected_credits = max(account.unreflected_credits + new_usage - reflected, Decimal(0))
    account.local_credits_seen = total
    account.observed_consumed_units = consumed
    account.save()
    return max(int((Decimal(str(meter.balance)) - account.unreflected_credits).to_integral_value(rounding=ROUND_FLOOR)), 0)
