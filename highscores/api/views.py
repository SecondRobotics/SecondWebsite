from django.shortcuts import redirect
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from discordoauth2.models import User
from highscores.api.serializers import UserSerializer


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
def auth(request: Request) -> Response:
    """Authenticates the user."""
    if request.user.is_authenticated:
        # Redirect to localhost:22226 with the sessionid as a query parameter.
        return redirect('http://localhost:22226/?sessionid=%s' % request.session.session_key)
    else:
        return redirect('/oauth2/loginapi')


@api_view(['POST'])
def submit(request: Request) -> Response:
    """Submits a score."""
    if not request.user.is_authenticated:
        return Response({'success': False, 'message': 'User is not authenticated.'})

    return Response({'success': False, 'message': 'Not implemented yet.'})
