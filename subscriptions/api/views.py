from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from discordoauth2.models import User
from subscriptions.models import ServerSession
from subscriptions import orchestrator
from subscriptions.services import (
    SubscriptionError,
    entitlement_payload,
    heartbeat_server_session,
    launch_casual_server,
    process_orchestrator_event,
    request_stop_server_session,
    serialize_session,
)


def _require_auth(request):
    if not request.user.is_authenticated:
        return Response({'success': False, 'message': 'User is not authenticated.'}, status=401)
    return None


def _auth_token_key(request):
    auth = getattr(request, 'auth', None)
    return getattr(auth, 'key', None) or (str(auth) if auth else '')


def _is_service_request(request):
    expected = getattr(settings, 'SECONDWEBSITE_SERVICE_TOKEN', '')
    return bool(expected and _auth_token_key(request) == expected)


def _resolve_launch_user(request):
    if _is_service_request(request):
        owner_discord_id = (request.data or {}).get('owner_discord_id') or (request.data or {}).get('ownerDiscordUserId')
        if not owner_discord_id:
            raise SubscriptionError('Service launch requests require owner_discord_id.')
        try:
            return User.objects.get(id=owner_discord_id)
        except User.DoesNotExist as exc:
            raise SubscriptionError('The requested Discord user is not linked to SecondWebsite.') from exc
    return request.user


@api_view(['GET'])
def my_entitlement(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    return Response({'success': True, 'entitlement': entitlement_payload(request.user)})


@api_view(['GET'])
def user_entitlement(request, discord_user_id):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    if not _is_service_request(request):
        return Response({'success': False, 'message': 'Service token is required.'}, status=403)
    try:
        user = User.objects.get(id=discord_user_id)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'The requested Discord user is not linked to SecondWebsite.'}, status=404)
    return Response({'success': True, 'discord_user_id': str(user.id), 'entitlement': entitlement_payload(user)})


@api_view(['GET'])
def casual_games(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    try:
        games = orchestrator.get_casual_games()
    except orchestrator.OrchestratorError as exc:
        return Response({'success': False, 'message': str(exc), 'code': exc.code}, status=503)
    return Response({'success': True, 'games': games})


@api_view(['POST'])
def start_session(request):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error

    data = request.data or {}
    game_code = data.get('game_code') or data.get('gameCode')
    if not game_code:
        return Response({'success': False, 'message': 'game_code is required.'}, status=400)

    try:
        launch_user = _resolve_launch_user(request)
        session = launch_casual_server(
            launch_user,
            requested_minutes=data.get('requested_minutes') or data.get('requestedMinutes'),
            game=data.get('game', '') or str(game_code),
            game_code=game_code,
            comment=data.get('comment', ''),
            password=data.get('password', ''),
            launch_source=data.get('launch_source') or data.get('launchSource') or ('discord_bot' if _is_service_request(request) else 'website'),
            launch_context=data.get('launch_context', {}),
        )
    except SubscriptionError as exc:
        return Response({'success': False, 'message': str(exc), 'code': exc.code}, status=exc.status_code)

    return Response({'success': True, 'session': serialize_session(session)}, status=201)


@api_view(['POST'])
def stop_session(request, session_id):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error

    try:
        query = ServerSession.objects
        if not _is_service_request(request):
            query = query.filter(user=request.user)
        session = query.get(id=session_id)
    except ServerSession.DoesNotExist:
        return Response({'success': False, 'message': 'Server session does not exist.'}, status=404)

    try:
        session = request_stop_server_session(session, reason=(request.data or {}).get('reason', 'stopped'))
    except SubscriptionError as exc:
        return Response({'success': False, 'message': str(exc), 'code': exc.code}, status=exc.status_code)
    return Response({'success': True, 'session': serialize_session(session)})


@api_view(['POST'])
def heartbeat_session(request, session_id):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error

    try:
        session = ServerSession.objects.get(id=session_id, user=request.user)
    except ServerSession.DoesNotExist:
        return Response({'success': False, 'message': 'Server session does not exist.'}, status=404)

    try:
        session = heartbeat_server_session(session, server_identifier=(request.data or {}).get('server_identifier', ''))
    except SubscriptionError as exc:
        return Response({'success': False, 'message': str(exc)}, status=409)
    return Response({'success': True, 'session': serialize_session(session)})


@api_view(['POST'])
def orchestrator_event(request, session_id):
    auth_error = _require_auth(request)
    if auth_error:
        return auth_error
    if not _is_service_request(request):
        return Response({'success': False, 'message': 'Service token is required.'}, status=403)

    try:
        event = process_orchestrator_event(session_id, request.data or {})
    except ServerSession.DoesNotExist:
        return Response({'success': False, 'message': 'Server session does not exist.'}, status=404)
    except SubscriptionError as exc:
        return Response({'success': False, 'message': str(exc)}, status=400)

    return Response({'success': True, 'event_id': event.event_id, 'status': event.status})
