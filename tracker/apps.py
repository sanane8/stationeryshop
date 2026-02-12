from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'
    
    def ready(self):
        # Import signals to ensure handlers are connected
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid raising during migrations or when signals import fails
            pass
