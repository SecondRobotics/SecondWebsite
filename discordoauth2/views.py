from django.http import JsonResponse, HttpRequest
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
import requests

from SRCweb.settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI, DISCORD_AUTH_URL

DISCORD_API_ENDPOINT = 'https://discord.com/api/v8'


@login_required(login_url="/oauth2/login")
def get_authenticated_user(request: HttpRequest) -> JsonResponse:
    return JsonResponse({ "user": request.user })

def discord_login(request: HttpRequest):
    return redirect(DISCORD_AUTH_URL)

def discord_login_redirect(request: HttpRequest):
    user = exchange_code(request.GET.get('code'))
    discord_user = authenticate(request, user=user)
    login(request, discord_user)
    return redirect('/')

def exchange_code(code: str):
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': 'identify email',
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post('%s/oauth2/token' % DISCORD_API_ENDPOINT, data=data, headers=headers)
    response.raise_for_status()
    
    response = requests.get('%s/users/@me' % DISCORD_API_ENDPOINT, headers={
        'Authorization': 'Bearer %s' % response.json()['access_token']
    })
    
    return response.json()
    