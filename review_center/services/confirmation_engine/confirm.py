from .approval_engine import ApproveEngine
from .rejection_engine import RejectEngine
from review_center.models import AgentDecision

def call_engine(application):
    if application.status != 'pending':
        return None
    decision = AgentDecision.objects.values_list('recommendation', flat= True).get(application = application)
    if decision == "approve":
        ApproveEngine(application= application).accept()
    elif decision == "reject":
        RejectEngine(application= application).reject()
