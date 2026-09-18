from ..llmprocessor.response_processor import LLMResponseProcessor

class Analyzer:
    def __init__(self,  client ):
        self.client = client
        self.processor = LLMResponseProcessor()
        self.expected_schema = {
            "writing_score": int,
            "grammar_score": int,
            "readability_score": int,
            "structure_score": int,
            "overall_score": int,
            "summary": str,
            "strengths": list,
            "weaknesses": list
        }
        self.expected_schema_score=[
            "writing_score",
            "grammar_score",
            "readability_score",
            "structure_score",
            "overall_score"
        ]           

    def analyze_blog(self,title, content):
        prompt = self._build_analysis_prompt(title, content)

        response = self._call_model(prompt)
        if response is None:
            return "Invalid Response by AI try Again"
 
        analysis = self.processor.process_resp(response, expected_schema= self.expected_schema, expected_schema_score= self.expected_schema_score)

        return analysis

    def _build_analysis_prompt(self, title, content):
       return f"""Analyze the following blog post:
            You are a professional blog reviewer.
            Analyze the blog provided below.
            Return ONLY valid JSON.
            Required JSON structure:
            {{
            "writing_score": int,
            "grammar_score": int,
            "readability_score": int,
            "structure_score": int,
            "overall_score": int,
            "summary": str,
            "strengths": list,
            "weaknesses": list
            }}
            Rules:
            - Scores must be between 0 and 100
            - Do not return markdown
            - Do not explain your reasoning
            - Return only JSON
            BLOG TITLE: {title}

            BLOG CONTENT:
            {content}"""

    def _call_model(self, prompt):
        G_Client = self.client
        response = G_Client.prompt_sender(prompt)
        return response
