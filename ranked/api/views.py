from datetime import timezone
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from SRCweb.settings import API_KEY
from discordoauth2.models import User
from .lib import update_player_elos, validate_post_match_req_body, get_match_player_info
from ranked.api.serializers import EloHistorySerializer, GameModeSerializer, MatchSerializer, PlayerEloSerializer
from ranked.models import EloHistory, GameMode, Match, PlayerElo


@api_view(['GET'])
def ranked_api(request: Request) -> Response:
    return Response({
        'status': 'Online',
    })


@api_view(['GET'])
def get_game_mode(request: Request, game_mode_code: str) -> Response:
    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={
            'error': f'Game mode {game_mode_code} does not exist.'
        })

    serializer = GameModeSerializer(game_mode)
    matches_played = Match.objects.filter(game_mode=game_mode).count()
    players_count = PlayerElo.objects.filter(game_mode=game_mode).count()

    return Response({
        **serializer.data,
        'matches_played': matches_played,
        'players_count': players_count,
    })


@api_view(['GET'])
def get_player_stats(request: Request, game_mode_code: str, player_id: str) -> Response:
    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={
            'error': f'Game mode {game_mode_code} does not exist.'
        })

    try:
        player = User.objects.get(id=player_id)
    except User.DoesNotExist:
        return Response(status=404, data={
            'error': f'Player {player_id} does not exist.'
        })

    player_elo = PlayerElo.objects.get(player=player, game_mode=game_mode)

    if not player_elo.exists():
        return Response(status=404, data={
            'error': f'Player {player_id} has no elo history for {game_mode_code}.'
        })

    game_mode_serializer = GameModeSerializer(game_mode)
    player_elo_serializer = PlayerEloSerializer(player_elo)

    return Response({
        'display_name': player.display_name,
        'username': player.username,
        'avatar': player.avatar,
        **game_mode_serializer.data,
        **player_elo_serializer.data,
    })


@api_view(['GET'])
def get_player_elo_history(request: Request, game_mode_code: str, player_id: str) -> Response:
    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={
            'error': f'Game mode {game_mode_code} does not exist.'
        })

    try:
        player = User.objects.get(id=player_id)
    except User.DoesNotExist:
        return Response(status=404, data={
            'error': f'Player {player_id} does not exist.'
        })

    player_elo = PlayerElo.objects.get(player=player, game_mode=game_mode)

    if not elo_history.exists():
        return Response(status=404, data={
            'error': f'Player {player_id} has no elo history for {game_mode_code}.'
        })

    elo_history = EloHistory.objects.filter(player_elo=player_elo)

    player_elo_serializer = PlayerEloSerializer(player_elo)
    elo_history_serializer = EloHistorySerializer(elo_history, many=True)

    return Response({
        'display_name': player.display_name,
        'username': player.username,
        'avatar': player.avatar,
        **player_elo_serializer.data,
        'elo_history': elo_history_serializer.data,
    })


@api_view(['POST'])
def post_match_result(request: Request, game_mode_code: str) -> Response:
    """Post a match result.
    JSON body should be:
    {
        'red_alliance': [1111111111111111, 2222222222222222, 3333333333333333],
        'blue_alliance': [4444444444444444, 5555555555555555, 6666666666666666],
        'red_score': 3,
        'blue_score': 1,
    }
    """
    if request.META.get('HTTP_X_API_KEY') != API_KEY:
        return Response(status=401, data={
            'error': 'Invalid API key.'
        })

    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={
            'error': f'Game mode {game_mode_code} does not exist.'
        })

    players_per_alliance = game_mode.players_per_alliance

    body = request.data
    res = validate_post_match_req_body(body, players_per_alliance)
    if res:
        return res

    red_alliance = body['red_alliance']
    blue_alliance = body['blue_alliance']
    red_score = body['red_score']
    blue_score = body['blue_score']

    res, red_players, blue_players, red_player_elos, blue_player_elos = \
        get_match_player_info(red_alliance, blue_alliance, game_mode)
    if res:
        return res

    red_starting_elo = sum([elo.elo for elo in red_player_elos])
    blue_starting_elo = sum([elo.elo for elo in blue_player_elos])

    match = Match(
        game_mode=game_mode,
        red_alliance=red_players,
        blue_alliance=blue_players,
        red_score=red_score,
        blue_score=blue_score,
        red_starting_elo=red_starting_elo,
        blue_starting_elo=blue_starting_elo,
    )
    match.save()

    update_player_elos(match, red_starting_elo,
                       blue_starting_elo, red_player_elos, blue_player_elos)

    match_serializer = MatchSerializer(match)
    red_player_elos_serializer = PlayerEloSerializer(
        red_player_elos, many=True)
    blue_player_elos_serializer = PlayerEloSerializer(
        blue_player_elos, many=True)

    return Response({
        'match': match_serializer.data,
        'red_player_elos': red_player_elos_serializer.data,
        'blue_player_elos': blue_player_elos_serializer.data,
    })
