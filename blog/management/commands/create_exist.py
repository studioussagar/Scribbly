from django.core.management.base import BaseCommand
from blog.models import CustomUser, Profile

class Command(BaseCommand):
    help = "Create profiles for users missing one"

    def handle(self, *args, **kwargs):
        users_without_profile = CustomUser.objects.filter(profile__isnull=True)
        for user in users_without_profile:
            Profile.objects.create(user=user)
            self.stdout.write(f"Created profile for user: {user.username}")
        self.stdout.write("Done creating missing profiles.")
