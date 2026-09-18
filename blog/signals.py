from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile, CustomUser
from django.db.models.signals import pre_save

User = get_user_model()

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(pre_save, sender=CustomUser)
def sync_author_role(sender, instance, **kwargs):

    if instance.approved_for_author:
        instance.role = "author"
    else:
        instance.role = "viewer"