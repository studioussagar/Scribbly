from google import genai
import os
from dotenv import load_dotenv


load_dotenv()

class GeminiClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
    def prompt_sender(self,prompt):
        client = self.client
        try:
            response = client.models.generate_content(
                model = "gemini-3.1-flash-lite-preview",
                contents = prompt
            )
            return getattr(response,"text",str(response))
        except Exception as e:
            print("Gemini Error:", e)
            return None
