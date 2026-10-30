from django.core.management.base import BaseCommand

from subscriptions.models import UsageLedgerEntry
from subscriptions.services import sync_pending_polar_usage


class Command(BaseCommand):
    help = 'Retry pending or failed Polar usage events for premium casual server sessions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of usage entries to retry.',
        )

    def handle(self, *args, **options):
        entries = sync_pending_polar_usage(limit=options['limit'])
        sent = sum(1 for entry in entries if entry.polar_status == UsageLedgerEntry.POLAR_STATUS_SENT)
        failed = sum(1 for entry in entries if entry.polar_status == UsageLedgerEntry.POLAR_STATUS_FAILED)
        self.stdout.write(self.style.SUCCESS(f'Synced {sent} Polar usage event(s); {failed} still failed.'))
