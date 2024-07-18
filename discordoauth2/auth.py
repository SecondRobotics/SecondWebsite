from django.contrib.auth.backends import RemoteUserBackend
from .models import User
from typing import Union


class DiscordAuthenticationBackend(RemoteUserBackend):
    def authenticate(self, request, user) -> Union[User, None]:
        found_user = User.objects.filter(id=user['id'])
        if len(found_user) == 0:
            # New user (first time login)
            if user['email'] is None:
                return None
            new_user = User.objects.create_discord_user(user)
            return new_user
        # Returning user
        found_user = found_user[0]
        found_user.refresh_data(user)
        return found_user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
