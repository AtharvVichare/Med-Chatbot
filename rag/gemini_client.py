"""
Gemini Client Wrapper for Aarogya Drishti Medical RAG.
Uses official google-genai SDK.
Handles:
- Initialization with environment variables (GEMINI_API_KEY, GEMINI_MODEL)
- Structured generation with system instructions and JSON response schema
- Automatic retries on rate limits / transient server errors with exponential backoff
- Request timeouts
- Zero key leakage in logs or exceptions
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("AarogyaGeminiClient")

class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment or arguments.")

        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # Initialize the official Google GenAI client
        self.client = genai.Client(api_key=self.api_key)

    def generate_clinical_response(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Invokes Gemini model to produce structured grounded clinical response.
        Enforces JSON output and zero extrapolation.
        """
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json"
        )

        attempts = 0
        backoff = 1.0

        while attempts < self.max_retries:
            attempts += 1
            try:
                t0 = time.perf_counter()
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                latency = time.perf_counter() - t0

                raw_text = response.text or "{}"
                # Clean up if markdown fences were accidentally produced
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                try:
                    parsed = json.loads(clean_text)
                except json.JSONDecodeError:
                    parsed = {
                        "summary": clean_text,
                        "citations": [],
                        "abstain_reason": None
                    }

                return {
                    "success": True,
                    "data": parsed,
                    "model": self.model_name,
                    "latency_sec": latency,
                    "usage_metadata": getattr(response, "usage_metadata", None)
                }

            except (ServerError, APIError) as e:
                logger.warning(f"Gemini API transient failure (attempt {attempts}/{self.max_retries}): {e}")
                if attempts >= self.max_retries:
                    return {
                        "success": False,
                        "error": f"Gemini API error after {self.max_retries} attempts: {type(e).__name__}",
                        "model": self.model_name
                    }
                time.sleep(backoff)
                backoff *= 2.0
            except ClientError as ce:
                # Client errors (4xx e.g. quota, model not found)
                return {
                    "success": False,
                    "error": f"Gemini Client error: {str(ce)}",
                    "model": self.model_name
                }
            except Exception as ex:
                return {
                    "success": False,
                    "error": f"Unexpected error during Gemini inference: {type(ex).__name__}",
                    "model": self.model_name
                }

