from django.shortcuts import redirect
from django.http import HttpResponse, HttpRequest
from rest_framework.response import Response
from rest_framework.request import Request, Empty
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token

from discordoauth2.models import User
from .serializers import UserSerializer, ScoreWithLeaderboardSerializer, ScoreWithPlayerSerializer, LeaderboardSerializer
from ..models import Score, Leaderboard
from ..lib import submit_infinite_recharge, submit_rapid_react, submit_freight_frenzy, submit_tipping_point, submit_spin_up


@api_view(['GET'])
def get_session_validity(request: Request) -> Response:
    """Returns whether the user's session is valid or not."""
    if request.user.is_authenticated:
        serializer = UserSerializer(request.user)
        return Response({
            'valid': True,
            'user': serializer.data
        })
    else:
        return Response({'valid': False})


@api_view(['GET'])
def auth(request: HttpRequest) -> HttpResponse:
    """Authenticates the user."""
    if request.user.is_authenticated:
        # Upsert the user's token.
        token = Token.objects.get_or_create(user=request.user)[0]
        # Redirect to localhost:22226 with the token key as a query parameter.
        return redirect('http://localhost:22226/?token=%s' % token.key)
    else:
        return redirect('/oauth2/loginapi')


@api_view(['GET'])
def get_my_scores(request: Request) -> Response:
    """Returns the user's scores."""
    if not request.user.is_authenticated:
        return Response({'success': False, 'message': 'User is not authenticated.'})

    scores = Score.objects.filter(
        player=request.user, approved=True).order_by('-time_set')
    serializer = ScoreWithLeaderboardSerializer(scores, many=True)
    return Response({'success': True, 'scores': serializer.data})


@api_view(['GET'])
def get_player_scores(request: Request, user_id: int) -> Response:
    """Returns the player's scores."""
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, OverflowError):
        return Response({'success': False, 'message': 'User does not exist.'})

    scores = Score.objects.filter(
        player=user, approved=True).order_by('-time_set')
    serializer = ScoreWithLeaderboardSerializer(scores, many=True)
    return Response({'success': True, 'scores': serializer.data})


@api_view(['GET'])
def get_robot_leaderboard(request: Request, game: str, robot: str) -> Response:
    """Returns the leaderboard with the given robot name."""
    game = game.replace('_', ' ')
    robot = robot.replace('_', ' ')
    if not Leaderboard.objects.filter(robot=robot, game=game).exists():
        return Response({'success': False, 'message': 'Leaderboard does not exist.'})

    message = Leaderboard.objects.get(robot=robot, game=game).message

    scores = Score.objects.filter(leaderboard__robot=robot, leaderboard__game=game, approved=True).order_by(
        '-score', 'time_set').all()

    top_scores = scores[:10]
    serializer = ScoreWithPlayerSerializer(top_scores, many=True)

    self_score_data = None
    if request.user.is_authenticated:
        self_score = scores.filter(player=request.user).first()
        if self_score is not None:
            self_serializer = ScoreWithPlayerSerializer(self_score)
            self_score_data = self_serializer.data
            self_score_data['rank'] = scores.filter(score__gt=self_score.score).count(
            ) + scores.filter(score=self_score.score, time_set__lt=self_score.time_set).count() + 1

    return Response({'success': True, 'message': message, 'scores': serializer.data, 'self': self_score_data})


@api_view(['GET'])
def get_leaderboard(request: Request, leaderboard: str) -> Response:
    """Returns the leaderboard with the given name."""
    if not Leaderboard.objects.filter(name=leaderboard).exists():
        return Response({'success': False, 'message': 'Leaderboard does not exist.'})

    message = Leaderboard.objects.get(name=leaderboard).message

    scores = Score.objects.filter(leaderboard__name=leaderboard, approved=True).order_by(
        '-score', 'time_set').all()

    top_scores = scores[:10]
    serializer = ScoreWithPlayerSerializer(top_scores, many=True)

    self_score_data = None
    if request.user.is_authenticated:
        self_score = scores.filter(player=request.user).first()
        if self_score is not None:
            self_serializer = ScoreWithPlayerSerializer(self_score)
            self_score_data = self_serializer.data
            self_score_data['rank'] = scores.filter(score__gt=self_score.score).count(
            ) + scores.filter(score=self_score.score, time_set__lt=self_score.time_set).count() + 1

    return Response({'success': True, 'message': message, 'scores': serializer.data, 'self': self_score_data})


@api_view(['GET'])
def get_game_leaderboards(request: Request, game: str) -> Response:
    """Returns a list of leaderboards with the given game slug or game name."""
    game = game.replace('_', ' ')
    if Leaderboard.objects.filter(game_slug=game).exists():
        leaderboards = Leaderboard.objects.filter(game_slug=game).all()
    elif Leaderboard.objects.filter(game=game).exists():
        leaderboards = Leaderboard.objects.filter(game=game).all()
    else:
        return Response({'success': False, 'message': 'No leaderboards exist for that game.'})

    serializer_data = LeaderboardSerializer(leaderboards, many=True).data

    # Append a link to each leaderboard.
    for leaderboard in serializer_data:
        leaderboard['link'] = f'https://secondrobotics.org/highscores/{leaderboard["game_slug"]}/{leaderboard["name"]}/'

    # FIXME: rename scores to leaderboards
    return Response({'success': True, 'scores': serializer_data})


@api_view(['GET'])
def get_leaderboards(request: Request) -> Response:
    """Returns a list of all leaderboards."""
    leaderboards = Leaderboard.objects.all()
    serializer_data = LeaderboardSerializer(leaderboards, many=True).data

    # Append a link to each leaderboard.
    for leaderboard in serializer_data:
        leaderboard['link'] = f'https://secondrobotics.org/highscores/{leaderboard["game_slug"]}/{leaderboard["name"]}/'

    return Response({'success': True, 'leaderboards': serializer_data})


@api_view(['GET'])
def get_games(request: Request) -> Response:
    """Returns a list of all games."""
    games = Leaderboard.objects.values_list('game', flat=True).distinct()
    return Response({'success': True, 'games': games})


@api_view(['POST'])
def submit(request: Request) -> Response:
    """Submits a score."""
    if not request.user.is_authenticated:
        return Response({'success': False, 'message': 'User is not authenticated.'})

    if not request.data or request.data is Empty:
        return Response({'success': False, 'message': 'No data was provided.'})
    data = request.data  # type: ignore
    data = data  # type: dict

    # Get the score from the request.
    score = data.get('score', None)  # type: int | None
    robot = data.get('robot', None)  # type: str | None
    game = data.get('game', None)  # type: str | None
    source = data.get('source', 'https://i.imgur.com/bUUfB8c.png')  # type: str
    clean_code = data.get('clean_code', None)  # type: str | None

    if score is None:
        return Response({'success': False, 'message': 'Missing score.'})
    if robot is None:
        return Response({'success': False, 'message': 'Missing robot.'})
    if game is None:
        return Response({'success': False, 'message': 'Missing game.'})
    if clean_code is None:
        return Response({'success': False, 'message': 'Missing clean code.'})

    if not Leaderboard.objects.filter(robot=robot, game=game).exists():
        return Response({'success': False, 'message': 'Leaderboard does not exist.'})

    leaderboard_obj = Leaderboard.objects.get(robot=robot, game=game)
    if leaderboard_obj is None:
        return Response({'success': False, 'message': 'Invalid leaderboard.'})

    # Determine the leaderboard to submit to.
    if game == 'Infinite Recharge':
        submit_score = submit_infinite_recharge
    elif game == 'Rapid React':
        submit_score = submit_rapid_react
    elif game == 'Freight Frenzy':
        submit_score = submit_freight_frenzy
    elif game == 'Tipping Point':
        submit_score = submit_tipping_point
    elif game == 'Spin Up':
        submit_score = submit_spin_up
    else:
        return Response({'success': False, 'message': 'Leaderboard provided is not supported yet.'})

    score_obj = Score()
    score_obj.leaderboard = leaderboard_obj
    score_obj.player = request.user
    score_obj.score = score
    score_obj.source = source
    score_obj.clean_code = clean_code

    # Submit the score.
    res = submit_score(score_obj)
    if res is not None:
        return Response({'success': False, 'message': res})

    return Response({'success': True, 'message': 'Score submitted.'})
