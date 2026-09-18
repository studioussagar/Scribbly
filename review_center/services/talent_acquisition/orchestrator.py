from ..application_analyzer import ApplicationAnalyzer
from ..decision_agent import DecisionAgent
from ..risk_assessment import RiskAssessmentAgent
from ..confirmation_engine.confirm import call_engine

class TalentAcquisitionOrchestrate:
    def __init__(self):
        ...

    def process(self, application):
        ApplicationAnalyzer( application ).analyze()
        RiskAssessmentAgent( application).assess()
        DecisionAgent(application).decide()
        call_engine(application)