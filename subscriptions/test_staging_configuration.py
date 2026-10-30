import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlparse


def test_oauth_uses_the_test_application_and_registered_redirects():
    env = {**os.environ, 'DISCORD_CLIENT_ID': '123456789',
           'DISCORD_REDIRECT_URI': 'http://localhost:8000/oauth2/login/redirect',
           'DISCORD_API_REDIRECT_URI': 'http://localhost:8000/oauth2/loginapi/redirect'}
    script = ('import json; from SRCweb import settings as s; '
              'print(json.dumps([s.DISCORD_AUTH_URL, s.DISCORD_AUTH_API_URL]))')
    output = subprocess.check_output([sys.executable, '-c', script], env=env,
                                     cwd=Path(__file__).resolve().parents[1], text=True)
    for url, target in zip(json.loads(output), [env['DISCORD_REDIRECT_URI'], env['DISCORD_API_REDIRECT_URI']]):
        query = parse_qs(urlparse(url).query)
        assert query['client_id'] == ['123456789']
        assert query['redirect_uri'] == [target]
        assert query['scope'] == ['identify email']
