from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, ExpressionWrapper, F, FloatField, Max, Min, Case, When, Value
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
import math
from SRCweb.settings import API_KEY
from discordoauth2.models import User
from .lib import revert_player_elos, update_player_elos, validate_patch_match_req_body, validate_post_match_req_body, get_match_player_info
from ranked.api.serializers import EloHistorySerializer, GameModeSerializer, MatchSerializer, PlayerEloSerializer
from ranked.models import EloHistory, GameMode, Match, PlayerElo
from ranked.templatetags.rank_filter import mmr_to_rank
from .serializers import LeaderboardSerializer
from django.db.models.functions import Exp
from django.http import JsonResponse

@api_view(['GET'])
def ranked_api(request: Request) -> Response:
    """
    Gets a list of all the available game modes for ranked play.
    """

    # Sort the game modes by the number of matches played within the last week
    game_modes = GameMode.objects.annotate(
        match_count=Count(
            'match',
            filter=Q(match__time__gte=timezone.now() - timedelta(days=7))
        )
    ).order_by('-match_count')

    game_mode_serializer = GameModeSerializer(game_modes, many=True)
    return Response(game_mode_serializer.data)


@api_view(['GET'])
def get_leaderboard(request: Request, game_mode_code: str) -> Response:
    """
    Gets the leaderboard for a particular game mode.
    """
    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={'error': f'Game mode {game_mode_code} does not exist.'})

    players = PlayerElo.objects.filter(game_mode=game_mode, matches_played__gt=20)
    players = players.annotate(
        time_delta=ExpressionWrapper(
            timezone.now() - F('last_match_played_time'),
            output_field=FloatField()
        ) / 3600000000
    )

    players = players.annotate(
        mmr = ExpressionWrapper(
        Case(
            # When time_delta > 168
            When(
                time_delta__gt=168,
                then=ExpressionWrapper(
                    150 * Exp(-0.00175 * (F('time_delta') - Value(168))) + F('elo') - 150,
                    output_field=FloatField()
                )
            ),
            # When time_delta <= 168
            When(
                time_delta__lte=168,
                then=F('elo')
            ),
            output_field=FloatField()
        ),
        output_field=FloatField()
    )
    )

    highest_mmr = players.aggregate(Max('mmr'))['mmr__max']
    lowest_mmr = players.aggregate(Min('mmr'))['mmr__min']

    players_with_rank = []
    for player in players:
        rank, color = mmr_to_rank(player.mmr, highest_mmr, lowest_mmr)
        players_with_rank.append({
            'player_id': player.player.id,
            'rank_number': player.mmr,
            'rank_name': rank,
        })

    players_with_rank = sorted(players_with_rank, key=lambda x: x['rank_number'], reverse=True)

    return Response(players_with_rank)

@api_view(['GET'])
def get_game_mode(request: Request, game_mode_code: str) -> Response:
    """
    Gets basic statistics for ranked matches played in a particular game mode.
    """
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
def get_player(request: Request, player_id: str) -> Response:
    """
    Gets whether the player has created an account in the system.
    """
    try:
        user = User.objects.get(id=player_id)
    except (User.DoesNotExist, ValueError):
        return Response(status=404, data={
            'exists': False
        })

    return Response({
        'exists': True,
        'display_name': str(user),
        'username': user.username,
        'avatar': user.avatar,
    })


@api_view(['GET'])
def get_player_stats(request: Request, game_mode_code: str, player_id: str) -> Response:
    """
    Gets statistics for a player in a particular game mode.
    """
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

    try:
        player_elo = PlayerElo.objects.get(player=player, game_mode=game_mode)
    except PlayerElo.DoesNotExist:
        return Response(status=404, data={
            'error': f'Player {player_id} has no elo history for {game_mode_code}.'
        })

    game_mode_serializer = GameModeSerializer(game_mode)
    player_elo_serializer = PlayerEloSerializer(player_elo)

    return Response({
        'display_name': str(player),
        'username': player.username,
        'avatar': player.avatar,
        **game_mode_serializer.data,
        **player_elo_serializer.data,
    })


@api_view(['GET'])
def get_player_elo_history(request: Request, game_mode_code: str, player_id: str) -> Response:
    """
    Gets the elo history and statistics for a player in a particular game mode.
    """
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

    elo_history = EloHistory.objects.filter(player_elo=player_elo)
    if not elo_history.exists():
        return Response(status=404, data={
            'error': f'Player {player_id} has no elo history for {game_mode_code}.'
        })

    player_elo_serializer = PlayerEloSerializer(player_elo)
    elo_history_serializer = EloHistorySerializer(elo_history, many=True)

    return Response({
        'display_name': str(player),
        'username': player.username,
        'avatar': player.avatar,
        **player_elo_serializer.data,
        'elo_history': elo_history_serializer.data,
    })


@api_view(['POST'])
def post_match_result(request: Request, game_mode_code: str) -> Response:
    """
    Post a match result.
    JSON body should be:
    {
        "red_alliance": [1111111111111111, 2222222222222222, 3333333333333333],
        "blue_alliance": [4444444444444444, 5555555555555555, 6666666666666666],
        "red_score": 3,
        "blue_score": 1
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

    res, red_players, blue_players, red_player_elos, blue_player_elos = get_match_player_info(
        red_alliance, blue_alliance, game_mode)
    if res:
        return res

    red_starting_elo = sum([elo.elo for elo in red_player_elos])
    blue_starting_elo = sum([elo.elo for elo in blue_player_elos])

    match = Match(
        game_mode=game_mode,
        red_score=red_score,
        blue_score=blue_score,
        red_starting_elo=red_starting_elo,
        blue_starting_elo=blue_starting_elo,
    )
    match.save()
    match.red_alliance.set(red_players)
    match.blue_alliance.set(blue_players)
    match.save()

    red_elo_changes, blue_elo_changes = update_player_elos(
        match, red_player_elos, blue_player_elos)

    match_serializer = MatchSerializer(match)
    red_player_elos_serializer = PlayerEloSerializer(
        red_player_elos, many=True)
    blue_player_elos_serializer = PlayerEloSerializer(
        blue_player_elos, many=True)
    red_display_names = [str(player) for player in red_players]
    blue_display_names = [str(player) for player in blue_players]

    return Response({
        'match': match_serializer.data,
        'red_player_elos': red_player_elos_serializer.data,
        'blue_player_elos': blue_player_elos_serializer.data,
        'red_display_names': red_display_names,
        'blue_display_names': blue_display_names,
        'red_elo_changes': red_elo_changes,
        'blue_elo_changes': blue_elo_changes,
    })


@api_view(['PATCH'])
def edit_match_result(request: Request, game_mode_code: str) -> Response:
    """
    Edit a match result. Can only edit the most recent match's score.
    JSON body should be:
    {
        "red_score": 3,
        "blue_score": 1
    }
    """
    if request.META.get('HTTP_X_API_KEY') != API_KEY:
        return Response(status=401, data={
            'error': 'Invalid API key.'
        })

    body = request.data
    res = validate_patch_match_req_body(body)
    if res:
        return res

    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={
            'error': f'Game mode {game_mode_code} does not exist.'
        })

    match = Match.objects.filter(
        game_mode=game_mode).order_by('-match_number').first()
    if not match:
        return Response(status=404, data={
            'error': f'No matches found for {game_mode_code}.'
        })

    red_players = match.red_alliance.all()
    blue_players = match.blue_alliance.all()
    red_player_elos = PlayerElo.objects.filter(
        player__in=red_players, game_mode=game_mode)
    blue_player_elos = PlayerElo.objects.filter(
        player__in=blue_players, game_mode=game_mode)

    red_elo_history = EloHistory.objects.filter(
        match_number=match.match_number, player_elo__in=red_player_elos)
    blue_elo_history = EloHistory.objects.filter(
        match_number=match.match_number, player_elo__in=blue_player_elos)

    revert_player_elos(match, red_elo_history, blue_elo_history)

    match.red_score = body['red_score']
    match.blue_score = body['blue_score']
    match.time = timezone.now()
    match.save()

    red_player_elos = PlayerElo.objects.filter(
        player__in=red_players, game_mode=game_mode)
    blue_player_elos = PlayerElo.objects.filter(
        player__in=blue_players, game_mode=game_mode)

    red_elo_changes, blue_elo_changes = update_player_elos(
        match, list(red_player_elos), list(blue_player_elos))

    match_serializer = MatchSerializer(match)
    red_player_elos_serializer = PlayerEloSerializer(
        red_player_elos, many=True)
    blue_player_elos_serializer = PlayerEloSerializer(
        blue_player_elos, many=True)
    red_display_names = [str(player) for player in red_players]
    blue_display_names = [str(player) for player in blue_players]

    return Response({
        'match': match_serializer.data,
        'red_player_elos': red_player_elos_serializer.data,
        'blue_player_elos': blue_player_elos_serializer.data,
        'red_display_names': red_display_names,
        'blue_display_names': blue_display_names,
        'red_elo_changes': red_elo_changes,
        'blue_elo_changes': blue_elo_changes,
    })

@api_view(['GET'])
def get_valid_players(request: Request, game_mode_code: str) -> Response:
    """
    Gets a list of all valid players for a particular game mode.
    """
    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={'error': f'Game mode {game_mode_code} does not exist.'})

    valid_players = PlayerElo.objects.filter(game_mode=game_mode).select_related('player')
    
    players_data = [{
        'id': player_elo.player.id,
        'display_name': str(player_elo.player),
        'username': player_elo.player.username,
        'avatar': player_elo.player.avatar,
        'elo': player_elo.elo
    } for player_elo in valid_players]

    return Response(players_data)

@api_view(['GET'])
def get_all_users(request: Request) -> Response:
    """
    Gets a list of all registered users.
    """
    users = User.objects.all()
    users_data = [{
        'id': user.id,
        'display_name': str(user),
        'username': user.username,
        'avatar': user.avatar,
    } for user in users]

    return Response(users_data)

@api_view(['POST'])
def change_match_game_modes(request: Request) -> Response:
    """
    Changes the game mode of specified matches.
    """
    if request.META.get('HTTP_X_API_KEY') != API_KEY:
        return Response(status=401, data={
            'error': 'Invalid API key.'
        })

    if 'matches' not in request.data or not isinstance(request.data['matches'], list):
        return Response(status=400, data={'error': 'Invalid request format. Expected a list of matches.'})

    results = []
    for match_data in request.data['matches']:
        if 'new_game_mode' not in match_data or 'match_number' not in match_data:
            results.append({'error': 'Invalid match data format. Expected new_game_mode and match_number.'})
            continue

        try:
            match = Match.objects.get(match_number=match_data['match_number'])
        except Match.DoesNotExist:
            results.append({'error': f"Match {match_data['match_number']} does not exist."})
            continue

        try:
            new_game_mode = GameMode.objects.get(short_code=match_data['new_game_mode'])
        except GameMode.DoesNotExist:
            results.append({'error': f"Game mode {match_data['new_game_mode']} does not exist."})
            continue

        # Define old_game_mode from the match instance
        old_game_mode = match.game_mode

        # Proceed with changing the game mode
        match.game_mode = new_game_mode
        match.time = timezone.now()
        match.save()

        red_players = match.red_alliance.all()
        blue_players = match.blue_alliance.all()
        red_player_elos = PlayerElo.objects.filter(player__in=red_players, game_mode=old_game_mode)
        blue_player_elos = PlayerElo.objects.filter(player__in=blue_players, game_mode=old_game_mode)

        red_elo_history = EloHistory.objects.filter(
            match_number=match.match_number, player_elo__in=red_player_elos)
        blue_elo_history = EloHistory.objects.filter(
            match_number=match.match_number, player_elo__in=blue_player_elos)

        revert_player_elos(match, red_elo_history, blue_elo_history)

        red_player_elos = PlayerElo.objects.filter(player__in=red_players, game_mode=new_game_mode)
        blue_player_elos = PlayerElo.objects.filter(player__in=blue_players, game_mode=new_game_mode)

        red_elo_changes, blue_elo_changes = update_player_elos(
            match, list(red_player_elos), list(blue_player_elos))

        match_serializer = MatchSerializer(match)
        red_player_elos_serializer = PlayerEloSerializer(red_player_elos, many=True)
        blue_player_elos_serializer = PlayerEloSerializer(blue_player_elos, many=True)
        red_display_names = [str(player) for player in red_players]
        blue_display_names = [str(player) for player in blue_players]

        results.append({
            'match': match_serializer.data,
            'red_player_elos': red_player_elos_serializer.data,
            'blue_player_elos': blue_player_elos_serializer.data,
            'red_display_names': red_display_names,
            'blue_display_names': blue_display_names,
            'red_elo_changes': red_elo_changes,
            'blue_elo_changes': blue_elo_changes,
            'old_game_mode': old_game_mode.short_code,
            'new_game_mode': new_game_mode.short_code,
            'status': 'success'
        })

    return Response(results)

@api_view(['POST'])
def clear_leaderboard(request: Request) -> Response:
    """
    Clears the leaderboard for a specific game mode.
    """
    if request.META.get('HTTP_X_API_KEY') != API_KEY:
        return Response(status=401, data={'error': 'Invalid API key.'})

    game_mode_code = request.data.get('game_mode')
    if not game_mode_code:
        return Response(status=400, data={'error': 'Game mode code is required.'})

    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={'error': f'Game mode {game_mode_code} does not exist.'})

    PlayerElo.objects.filter(game_mode=game_mode).delete()
    return Response(status=200, data={'message': 'Leaderboard cleared successfully.'})


@api_view(['POST'])
def recalculate_elo(request: Request) -> Response:
    """
    Recalculates the ELO for a specific game mode.
    """
    if request.META.get('HTTP_X_API_KEY') != API_KEY:
        return Response(status=401, data={'error': 'Invalid API key.'})

    game_mode_code = request.data.get('game_mode')
    if not game_mode_code:
        return Response(status=400, data={'error': 'Game mode code is required.'})

    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={'error': f'Game mode {game_mode_code} does not exist.'})

    # Ensure all players have PlayerElo objects
    matches = Match.objects.filter(game_mode=game_mode).order_by('time')
    all_players = set()
    for match in matches:
        all_players.update(match.red_alliance.all())
        all_players.update(match.blue_alliance.all())

    for player in all_players:
        PlayerElo.objects.get_or_create(
            player=player,
            game_mode=game_mode,
            defaults={'elo': 1200}
        )

    # Reset ELO to a base value
    players = PlayerElo.objects.filter(game_mode=game_mode)
    for player in players:
        player.elo = 1200  # Reset ELO to a base value
        player.save()

    for match in matches:
        red_players = match.red_alliance.all()
        blue_players = match.blue_alliance.all()
        red_player_elos = PlayerElo.objects.filter(player__in=red_players, game_mode=game_mode)
        blue_player_elos = PlayerElo.objects.filter(player__in=blue_players, game_mode=game_mode)

        red_elo_changes, blue_elo_changes = update_player_elos(
            match, list(red_player_elos), list(blue_player_elos))

        for player_elo, elo_change in zip(red_player_elos, red_elo_changes):
            player_elo.elo += elo_change
            player_elo.save()

        for player_elo, elo_change in zip(blue_player_elos, blue_elo_changes):
            player_elo.elo += elo_change
            player_elo.save()

    return Response(status=200, data={'message': 'ELO recalculated successfully.'})

@api_view(['GET'])
def get_stats(request):
    period = request.GET.get('period', 'month')
    
    # Calculate the start time based on the period
    now = timezone.now()
    if period == 'day':
        start_time = now - timedelta(days=1)
    elif period == 'week':
        start_time = now - timedelta(weeks=1)
    elif period == 'month':
        start_time = now - timedelta(days=30)
    elif period == 'year':
        start_time = now - timedelta(days=365)
    else:  # all time
        start_time = None

    # Get all game modes
    game_modes = GameMode.objects.all()
    stats = {}

    # Track game totals for sorting and overall totals
    game_totals = {}
    overall_matches = 0
    all_unique_players = set()
    total_artificial_players = 0
    
    for game_mode in game_modes:
        # Base queryset for this game mode
        matches = Match.objects.filter(game_mode=game_mode)
        
        # Apply time filter if not 'all'
        if start_time:
            matches = matches.filter(time__gte=start_time)

        # Get match count
        match_count = matches.count()

        # Get unique players with prefetch to reduce queries
        all_players = set()
        matches_with_players = matches.prefetch_related('red_alliance', 'blue_alliance')
        for match in matches_with_players:
            all_players.update(match.red_alliance.all())
            all_players.update(match.blue_alliance.all())
        unique_players = len(all_players)

        # Track totals per game for sorting (with artificial data)
        if game_mode.game not in game_totals:
            game_totals[game_mode.game] = 0

        # Add artificial data for specific game modes (for testing purposes)
        artificial_matches = 0
        artificial_players = 0
        
        if start_time is None:  # Only add artificial data for 'all' period
            if game_mode.short_code == 'IR3v3':  # Infinite Recharge 3v3
                artificial_matches = 10000
                artificial_players = 100
            elif game_mode.short_code == 'RR3v3':  # Rapid React 3v3
                artificial_matches = 3756
                artificial_players = 50
            elif game_mode.short_code == 'CU2v2':  # Change Up 2v2
                artificial_matches = 255
                artificial_players = 20
        
        final_match_count = match_count + artificial_matches
        final_unique_players = unique_players + artificial_players

        # Add to game totals (for sorting)
        game_totals[game_mode.game] += final_match_count

        # Add to overall totals
        overall_matches += final_match_count
        all_unique_players.update(all_players)
        total_artificial_players += artificial_players

        stats[game_mode.short_code] = {
            'matches': final_match_count,
            'unique_players': final_unique_players,
            'game': game_mode.game
        }

    # Calculate estimated time played (4 minutes per match)
    estimated_minutes = overall_matches * 4
    
    # Add game totals and overall totals to response
    response_data = {
        'stats': stats,
        'game_totals': game_totals,
        'overall': {
            'total_matches': overall_matches,
            'total_unique_players': len(all_unique_players) + total_artificial_players,
            'estimated_minutes_played': estimated_minutes
        }
    }

    return Response(response_data)
