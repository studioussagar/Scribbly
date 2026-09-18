from review_center.models import WriterApplication,ApplicationAnalysis
from ..services.ai_client.client.gemini_client import GeminiClient
from ..services.ai_client.agents.analyzer import Analyzer

class ApplicationAnalyzer:
    def __init__(self, application: WriterApplication):
        self.application = application
        self.title = application.submitted_title or ""
        self.content = application.submitted_content or ""

    def analyze(self):
        ai_client = GeminiClient()
        analyzer_object = Analyzer(ai_client)
        application_analysis = analyzer_object.analyze_blog(self.title,self.content)
        if type(application_analysis) != dict:
            return None

        analysis,created = (ApplicationAnalysis.objects.update_or_create(

            application=self.application,
            defaults={
                "writing_score": application_analysis["writing_score"],
                "grammar_score": application_analysis["grammar_score"],
                "readability_score": application_analysis["readability_score"],
                "structure_score": application_analysis["structure_score"],
                "summary": application_analysis["summary"],
                "overall_score": application_analysis["overall_score"],
                "strengths":application_analysis["strengths"],
                "weaknesses":application_analysis["weaknesses"],
                }
            )
        )
        return analysis
