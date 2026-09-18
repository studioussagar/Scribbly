from review_center.models import (WriterApplication,ApplicationAnalysis,RiskAssessment,AgentDecision)
from ..services.ai_client.client.gemini_client import GeminiClient
from ..services.ai_client.agents.decision_assessor import Decision



class DecisionAgent:
    def __init__(self, application: WriterApplication):
        self.application = application

    def decide(self):

        ai_client = GeminiClient()
        decision_object = Decision(ai_client)
        
        summary = ApplicationAnalysis.objects.values_list('summary', flat=True).get(application = self.application)
        overall_score = ApplicationAnalysis.objects.values_list('overall_score', flat=True).get(application = self.application)
        risk = RiskAssessment.objects.get(application=self.application)

        decided = decision_object.decide(summary, overall_score, risk)
        if type(decided) != dict:
            return None
        
        decision, created = (AgentDecision.objects.update_or_create(
            application=self.application,
            defaults={
                "recommendation": decided["recommendation"],
                "confidence": decided["confidence"],
                "reasoning": decided["reasoning"]
            }
        )
    )
        return decision

