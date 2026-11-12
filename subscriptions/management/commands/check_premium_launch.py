from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from subscriptions.models import SubscriptionPlan, UsageLedgerEntry, WebhookEvent


class Command(BaseCommand):
    help = 'Check premium launch configuration without printing secrets or contacting services.'

    def handle(self, *args, **options):
        issues = []
        for name in ['API_KEY', 'POLAR_ACCESS_TOKEN', 'POLAR_WEBHOOK_SECRET', 'POLAR_CASUAL_SERVER_METER_ID',
                     'POLAR_CUSTOMER_PORTAL_URL', 'ORCHESTRATOR_API_BASE_URL', 'ORCHESTRATOR_API_TOKEN']:
            value = getattr(settings, name, '')
            if not value or value in {name, 'replace-me', 'changeme'}:
                issues.append(f'Configure {name}.')
        for plan in SubscriptionPlan.objects.filter(is_active=True):
            if not plan.polar_product_id:
                issues.append(f'Map the {plan.tier} plan to its Polar product in Django admin.')
        if not SubscriptionPlan.objects.filter(is_active=True).exists():
            issues.append('Configure at least one active subscription plan.')
        failed_usage = UsageLedgerEntry.objects.filter(polar_status='failed').count()
        failed_hooks = WebhookEvent.objects.filter(status='failed').count()
        if failed_usage or failed_hooks:
            issues.append(f'Resolve {failed_usage} failed usage entries and {failed_hooks} failed webhook events.')
        self.stdout.write(f'Polar environment: {settings.POLAR_SERVER}')
        for issue in issues:
            self.stderr.write(issue)
        if issues:
            raise CommandError(f'{len(issues)} premium launch prerequisite(s) remain.')
        self.stdout.write(self.style.SUCCESS('Local prerequisites pass. Complete the sandbox and Linux/Discord acceptance checklist.'))
