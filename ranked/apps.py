from django.apps import AppConfig


class RankedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ranked'

    def ready(self):
        from django.db.utils import OperationalError, ProgrammingError
        from ranked.models import GameMode
        from ranked.api.lib import _margin_stats, _load_margin_stats
        try:
            for gm in GameMode.objects.values_list("id", flat=True):
                _margin_stats[gm] = _load_margin_stats(gm)
        except (OperationalError, ProgrammingError):
            pass
