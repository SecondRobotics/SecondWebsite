from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from SRCweb.settings import API_KEY
from ranked.models import GameMode, Match

# POST requests are protected by the API key with
# if request.META.get('HTTP_X_API_KEY') != API_KEY:
#         return Response(status=401)

@api_view(['GET'])
def get_status(request: Request):
    return Response({
        'status': 'Online',
    })

@api_view(['GET'])
def get_game_mode_status(request: Request, game_mode_code: str) -> Response:
    try:
        game_mode = GameMode.objects.get(short_code=game_mode_code)
    except GameMode.DoesNotExist:
        return Response(status=404, data={
            'error': f'Game mode {game_mode_code} does not exist.'
        })
    
    matches_played = Match.objects.filter(game_mode=game_mode).count()

    return Response({
        'game_mode': game_mode.name,
        'game': game_mode.game,
        'players_per_alliance': game_mode.players_per_alliance,
        'matches_played': matches_played,
    })

