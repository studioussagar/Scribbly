from review_center.models import (WriterApplication,RiskAssessment,ApplicationAnalysis)
from ..services.ai_client.client.gemini_client import GeminiClient
from ..services.ai_client.agents.risk_assessor import RiskAssessor

class RiskAssessmentAgent:
    def __init__(self, application: WriterApplication):
        self.application = application
        self.title = application.submitted_title or ""
        self.content = application.submitted_content or ""

    def assess(self):

        ai_client = GeminiClient()
        risk_object = RiskAssessor(ai_client)

        summary = ApplicationAnalysis.objects.values_list('summary', flat=True).get(application = self.application)

        assess = risk_object.assess_risk(self.title,self.content,summary)
        if type(assess) != dict:
            return None
        assessment, created = (
            RiskAssessment.objects.update_or_create(
            application=self.application,
            defaults={
                "risk_score": assess["risk_score"],
                "risk_level": assess["risk_level"],
                "toxicity_detected": assess["toxicity_detected"],
                "spam_detected": assess["spam_detected"],
                "suspicious_links": assess["suspicious_links"],
                "ai_generated_detected": assess["ai_generated_detected"],
                "overall_explanation": assess["explanation"],
            }
        )
    )

        return assessment
