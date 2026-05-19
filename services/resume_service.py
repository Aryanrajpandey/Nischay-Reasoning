import io
import json
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from services.llm import LLMService
import structlog

logger = structlog.get_logger()

class ResumeService:
    def __init__(self):
        self.llm = LLMService()

    def extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF or TXT file."""
        if filename.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(file_content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
            except Exception as e:
                logger.error("pdf_extraction_failed", error=str(e), filename=filename)
                return ""
        elif filename.lower().endswith(".txt"):
            return file_content.decode("utf-8", errors="ignore").strip()
        return ""

    async def analyze(self, text: str) -> List[Dict[str, Any]]:
        """Analyze resume text using LLM and return structured feedback."""
        if not text:
            return [{
                "priority": "high",
                "before": "No text detected in resume.",
                "after": "Ensure your resume is not a scanned image and contains selectable text.",
                "why": "Recruiters and ATS cannot read text from images. Use a standard PDF export."
            }]

        prompt = f"""
        You are an expert career coach and recruiter specializing in high-growth tech roles.
        Analyze the following resume text and provide 3-4 specific, actionable feedback items.
        
        For each item, provide:
        1. Priority: 'high', 'medium', or 'low'.
        2. Before: A snippet or description of the current weak point.
        3. After: A concrete improvement or rewrite.
        4. Why: The rationale from a recruiter/ATS perspective.

        Return the response ONLY as a JSON array of objects.
        Example format:
        [
          {{
            "priority": "high",
            "before": "Experienced in Python.",
            "after": "Built a real-time data pipeline using Python and Kafka...",
            "why": "Generic skills without context are ignored by ATS."
          }}
        ]

        Resume Text:
        {text[:4000]} 
        """

        try:
            response = await self.llm.completion([{"role": "user", "content": prompt}], temperature=0.3)
            # Find the JSON part in case the LLM adds text
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end != 0:
                return json.loads(response[start:end])
            return []
        except Exception as e:
            logger.error("resume_analysis_failed", error=str(e))
            return [{
                "priority": "high",
                "before": "Analysis system encountered an error.",
                "after": "Please try again in a few moments.",
                "why": "Transient backend error during LLM inference."
            }]
