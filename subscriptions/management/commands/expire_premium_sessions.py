from django.core.management.base import BaseCommand

from subscriptions.services import expire_stale_sessions


class Command(BaseCommand):
    help = 'Expire premium casual server sessions that have stopped heartbeating.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-heartbeat-age-minutes',
            type=int,
            default=10,
            help='How many minutes a running session can go without a heartbeat before expiring.',
        )

    def handle(self, *args, **options):
        expired = expire_stale_sessions(max_heartbeat_age_minutes=options['max_heartbeat_age_minutes'])
        self.stdout.write(self.style.SUCCESS(f'Expired {len(expired)} premium server session(s).'))
