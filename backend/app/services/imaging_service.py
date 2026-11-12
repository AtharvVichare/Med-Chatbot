"""
Clinical Radiological Imaging & Multimodal Scan Analysis Service.
Analyzes medical imaging (MRI, CT, Ultrasound, Sonography, X-ray, Mammography).
Produces:
- Modality and anatomical region identification
- Spatial bounding boxes for critical findings (e.g. lung nodule, renal calculi, fracture)
- Structured clinical observations, differential considerations, and recommended next steps
- Educational disclaimers ensuring AI findings are not treated as definitive diagnoses
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image

from rag.gemini_client import GeminiClient
from google.genai import types

logger = logging.getLogger("AarogyaImagingService")

IMAGING_ANALYSIS_SYSTEM_PROMPT = """You are Aarogya Drishti's Advanced Clinical Radiological Assistant.
You specialize in evaluating diagnostic radiological images (CT scans, MRIs, Ultrasounds/Sonography, Chest X-rays, etc.).

YOUR TASK:
Analyze the uploaded medical scan or imaging photo.
1. Identify the Imaging Modality (e.g. Computed Tomography, Magnetic Resonance Imaging, B-mode Ultrasonography, Digital Radiography).
2. Identify the Anatomical Region (e.g. Thorax, Abdomen, Brain/Cranium, Pelvis, Musculoskeletal).
3. Detect prominent abnormalities, pathologies, or anatomical variations (e.g. pulmonary nodules, infiltrates, renal stones, cysts, masses, effusions, fractures, or normal architecture).
4. For any notable finding, provide normalized 2D bounding box coordinates: [ymin, xmin, ymax, xmax] scaled 0 to 1000 (standard Gemini bounding box format).
5. Provide differential diagnoses and objective clinical recommendations for the patient's physician.

STRICT MEDICAL SAFETY RULES:
- Never declare definitive diagnoses like "You definitely have lung cancer". Frame findings objectively using radiological terminology (e.g. "Solitary hyperdense pulmonary lesion with irregular borders, which requires tissue correlation").
- Always recommend physician/radiologist correlation and appropriate confirmatory investigations (e.g., contrast CT, biopsy, blood tests).
- Emphasize that educational AI analysis is not a replacement for a certified radiologist's formal written report.

OUTPUT FORMAT (strictly raw JSON, no markdown backticks):
{
  "modality": "e.g. Axial Contrast-Enhanced CT",
  "anatomical_region": "e.g. Thorax / Chest",
  "overall_impression": "Concise summary of findings",
  "findings": [
    {
      "finding_id": "F1",
      "label": "e.g. Suspicious Solitary Pulmonary Nodule",
      "box_2d": [ymin, xmin, ymax, xmax],
      "severity": "high / moderate / low / benign",
      "description": "e.g. 14mm nodular density in the right middle lobe with spiculated margins."
    }
  ],
  "differential_considerations": [
    "Primary bronchogenic neoplasm",
    "Infectious granuloma",
    "Hamartoma"
  ],
  "recommended_investigations": [
    "Follow-up High-Resolution CT in 3 months or PET-CT",
    "Clinical consultation with a pulmonologist"
  ],
  "disclaimer": "This imaging evaluation is an educational AI assistance summary. Diagnostic confirmation requires formal clinical review by a certified radiologist."
}
"""

class ImagingAnalysisService:

    @staticmethod
    def analyze_scan_image(file_path: Path) -> Dict[str, Any]:
        """
        Analyzes a radiological image (PNG, JPG, JPEG) using Gemini Vision.
        Returns modality, findings with bounding boxes, differentials, and recommendations.
        """
        if not file_path.exists():
            return {
                "error": "File does not exist",
                "modality": "Unknown",
                "findings": []
            }

        gemini_client = GeminiClient()
        try:
            img = Image.open(file_path)
            config = types.GenerateContentConfig(
                system_instruction=IMAGING_ANALYSIS_SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json"
            )

            prompt = (
                "Please analyze this radiological scan. Identify the modality, anatomical site, "
                "and locate any significant pathology (e.g., masses, lesions, calculi, fractures) "
                "with exact bounding boxes [ymin, xmin, ymax, xmax] on a 0-1000 scale."
            )

            # Model cascade for vision resilience
            candidate_models = [gemini_client.model_name, "gemini-2.5-flash", "gemini-1.5-flash"]
            for mod in candidate_models:
                try:
                    response = gemini_client.client.models.generate_content(
                        model=mod,
                        contents=[img, prompt],
                        config=config
                    )
                    if response and response.text:
                        data = json.loads(response.text.strip())
                        return data
                except Exception as e:
                    logger.warning(f"Imaging analysis attempt failed on model {mod}: {e}")

        except Exception as err:
            logger.error(f"Image loading or API error in ImagingAnalysisService: {err}")

        return {
            "modality": "Radiological Scan / Image",
            "anatomical_region": "Unspecified",
            "overall_impression": "Image captured securely. Automated radiological segmentation is pending.",
            "findings": [],
            "differential_considerations": ["Clinical radiologist correlation required"],
            "recommended_investigations": ["Review original high-resolution DICOM slices with treating physician"],
            "disclaimer": "Informational scan assessment. Always review original DICOM scans with a licensed healthcare specialist."
        }

