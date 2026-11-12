"""Migrate a disposable SQLite backup; never mutate the source database."""
import argparse
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    target = Path(tempfile.mkdtemp(prefix='premium-migration-rehearsal-')) / 'db.sqlite3'
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(target) as backup:
            original.backup(backup)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SRCweb.settings')
    from django.conf import settings
    settings.DATABASES['default']['NAME'] = str(target)
    import django
    django.setup()
    from django.apps import apps
    from django.core.management import call_command
    from django.db import connection
    call_command('migrate', fake_initial=True, interactive=False)
    missing = []
    with connection.cursor() as cursor:
        for model in apps.get_models():
            if model._meta.app_label not in ['discordoauth2', 'events', 'highscores', 'home', 'ranked', 'subscriptions']:
                continue
            columns = {column.name for column in connection.introspection.get_table_description(cursor, model._meta.db_table)}
            missing.extend(f'{model._meta.db_table}.{field.column}' for field in model._meta.local_fields if field.column not in columns)
        cursor.execute('PRAGMA foreign_key_check')
        violations = len(cursor.fetchall())
    print(f'Rehearsal copy: {target}')
    print(f'Missing model columns: {missing}; foreign-key violations: {violations}')
    if missing or violations:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
