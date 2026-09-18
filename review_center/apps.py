from django.apps import AppConfig


class ReviewCenterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'review_center'
    def ready(self):
        import review_center.signals