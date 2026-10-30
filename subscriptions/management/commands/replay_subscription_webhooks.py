from django.core.management.base import BaseCommand, CommandError
from subscriptions.models import WebhookEvent
from subscriptions.services import process_polar_webhook


class Command(BaseCommand):
    help = 'Retry failed Polar subscription webhooks after correcting configuration.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        failed = 0
        events = list(WebhookEvent.objects.filter(provider='polar', status='failed').order_by('received_at')[:options['limit']])
        for event in events:
            try:
                process_polar_webhook(event.payload, event.event_id)
            except Exception:
                failed += 1
                self.stderr.write(f'Webhook {event.event_id} still failed; inspect its admin record.')
        self.stdout.write(f'Replayed {len(events) - failed} webhook(s); {failed} still failed.')
        if failed:
            raise CommandError('Some Polar webhooks still need attention.')
