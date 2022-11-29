from django.shortcuts import redirect
from django.http import HttpResponse, HttpRequest
from rest_framework.response import Response
from rest_framework.request import Request, Empty
from rest_framework.decorators import api_view

from .serializers import UserSerializer, ScoreSerializer, LeaderboardSerializer
from ..models import Score, Leaderboard


@api_view(['GET'])
def get_session_validity(request: Request) -> Response:
    """Returns whether the user's session is valid or not."""
    print(request.user)
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
        # Redirect to localhost:22226 with the sessionid as a query parameter.
        return redirect('http://localhost:22226/?sessionid=%s' % request.session.session_key)
    else:
        return redirect('/oauth2/loginapi')


@api_view(['GET'])
def get_my_scores(request: Request) -> Response:
    """Returns the user's scores."""
    if not request.user.is_authenticated:
        return Response({'success': False, 'message': 'User is not authenticated.'})

    scores = Score.objects.filter(player=request.user, approved=True)
    serializer = ScoreSerializer(scores, many=True)
    return Response({'success': True, 'scores': serializer.data})


@api_view(['GET'])
def get_leaderboard(request: Request, name: str) -> Response:
    """Returns the leaderboard with the given name."""
    if not Leaderboard.objects.filter(name=name).exists():
        return Response({'success': False, 'message': 'Leaderboard does not exist.'})

    scores = Score.objects.filter(leaderboard__name=name, approved=True).order_by(
        '-score', 'time_set').all()[:10]
    serializer = ScoreSerializer(scores, many=True)
    return Response({'success': True, 'scores': serializer.data})


@api_view(['GET'])
def get_leaderboards(request: Request) -> Response:
    """Returns all leaderboards."""
    leaderboards = Leaderboard.objects.all()
    serializer = LeaderboardSerializer(leaderboards, many=True)
    return Response({'success': True, 'leaderboards': serializer.data})


@api_view(['POST'])
def submit(request: Request) -> Response:
    """Submits a score."""
    if not request.user.is_authenticated:
        return Response({'success': False, 'message': 'User is not authenticated.'})

    if not request.data or request.data is Empty:
        return Response({'success': False, 'message': 'No data was provided.'})
    data = request.data

    # Get the score from the request.
    score = getattr(data, 'score', None)  # type: int | None
    leaderboard = getattr(data, 'leaderboard', None)  # type: str | None
    source = getattr(data, 'source_link', None)  # type: str | None
    clean_code = getattr(data, 'clean_code', None)  # type: str | None

    if score is None or leaderboard is None or source is None or clean_code is None:
        return Response({'success': False, 'message': 'Missing data.'})

    leaderboard_obj = Leaderboard.objects.get(name=leaderboard)
    if leaderboard_obj is None:
        return Response({'success': False, 'message': 'Invalid leaderboard.'})

    # Determine the leaderboard to submit to.
    if leaderboard == 'Infinite Recharge':
        from ..lib import submit_infinite_recharge as submit_score
    elif leaderboard == 'Rapid React':
        from ..lib import submit_rapid_react as submit_score
    elif leaderboard == 'Freight Frenzy':
        from ..lib import submit_freight_frenzy as submit_score
    elif leaderboard == 'Tipping Point':
        from ..lib import submit_tipping_point as submit_score
    elif leaderboard == 'Spin Up':
        from ..lib import submit_spin_up as submit_score
    else:
        return Response({'success': False, 'message': 'Invalid leaderboard.'})

    score_obj = Score()
    score_obj.leaderboard = leaderboard_obj
    score_obj.user = request.user  # type: ignore
    score_obj.score = score
    score_obj.source = source
    score_obj.clean_code = clean_code

    # Submit the score.
    res = submit_score(score_obj)
    if res is not None:
        return Response({'success': False, 'message': res})

    return Response({'success': True, 'message': 'Score submitted.'})
