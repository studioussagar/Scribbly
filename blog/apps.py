from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'

class YourAppConfig(AppConfig):
    name = 'blog'

    def ready(self):
        import blog.signals 