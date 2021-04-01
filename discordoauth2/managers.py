from django.contrib.auth import models

class DiscordUserOAuth2Manager(models.UserManager):
    def create_discord_user(self, user):
        return self.create(
            id = user['id'],
            username = user['username'],
            discriminator = user['discriminator'],
            avatar = "https://cdn.discordapp.com/avatars/%s/%s.webp" % (user['id'], user['avatar']),
            public_flags = user['public_flags'],
            flags = user['flags'],
            locale = user['locale'],
            mfa_enabled = user['mfa_enabled'],
            email = user['email'],
            verified = user['verified'],
        )
