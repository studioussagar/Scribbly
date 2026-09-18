from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import WriterApplication
from .services.talent_acquisition.orchestrator import TalentAcquisitionOrchestrate
from threading import Thread

def run_orchestrator(application_id ):
    application = WriterApplication.objects.get(pk = application_id)
    TalentAcquisitionOrchestrate().process(application)

@receiver(post_save, sender=WriterApplication )
def call_orchestrator(sender, instance, created, **kwargs):
    if created:
        thread = Thread(target= run_orchestrator,
                        args=(instance.pk,)
                    )
        (thread.start())