from django.core.validators import MinLengthValidator
from django.db import models
from .managers import DiscordUserOAuth2Manager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator

# Create your models here.

class User(AbstractUser):
    objects = DiscordUserOAuth2Manager()
    display_name_validator = ASCIIUsernameValidator()
    min_length_validator = MinLengthValidator(4)

    display_name = models.CharField(_('display name'), max_length=25, null=True, validators=[display_name_validator, min_length_validator])

    id = models.BigIntegerField(_('user id'), primary_key=True)
    username = models.CharField(_('username'), max_length=100)
    discriminator = models.CharField(_('discriminator'), max_length=4)
    avatar = models.URLField(_('avatar'))
    public_flags = models.IntegerField(_('public flags'))
    flags = models.IntegerField(_('flags'))
    locale = models.CharField(_('locale'), max_length=100)
    mfa_enabled = models.BooleanField(_('multi-factor authentication enabled'))
    email = models.EmailField(_('email address'))
    verified = models.BooleanField(
        _('email verified'),
        help_text=_('Whether the user has verified their email address.')
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['email']

    def __str__(self) -> str:
        if self.display_name:
            return self.display_name
        else:
            return self.username

    @property
    def get_full_name(self) -> str:
        return '%s#%s' % (self.username, self.discriminator)

    @property
    def get_short_name(self) -> str:
        if self.display_name:
            return self.display_name
        else:
            return self.username
    
    def update_last_login(self):
        """
        Updates the last_login date for the user logging in.
        """
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])

    def refresh_data(self, user):
        """
        Refreshes the Discord OAuth2 data upon login.
        """
        self.username = user['username']
        self.discriminator = user['discriminator']
        self.avatar = "https://cdn.discordapp.com/avatars/%s/%s.webp" % (user['id'], user['avatar'])
        self.public_flags = user['public_flags']
        self.flags = user['flags']
        self.locale = user['locale']
        self.mfa_enabled = user['mfa_enabled']
        self.email = user['email']
        self.verified = user['verified']

        self.update_last_login()
        self.save()
