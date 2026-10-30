import os
from pathlib import Path
import tempfile

import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_modify_db_settings():
    if not os.environ.get('ORCHESTRATOR_REPO'):
        yield
        return
    # Real callbacks use separate HTTP/DB threads. SQLite's shared in-memory
    # cache raises SQLITE_LOCKED instead of honoring the busy timeout. Exercise
    # the production file-backed locking behavior in an isolated test DB.
    with tempfile.TemporaryDirectory(prefix='premium-http-db-') as directory:
        settings.DATABASES['default'].setdefault('TEST', {})['NAME'] = str(Path(directory) / 'test.sqlite3')
        settings.DATABASES['default'].setdefault('OPTIONS', {})['timeout'] = 20
        yield
