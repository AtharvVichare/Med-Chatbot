"""
Patient Medical Document Processing & OCR/Text Extraction Service
Supports PDF, PNG, JPG, JPEG medical lab reports and clinical summaries.
Extracts dates, recognized tests (HbA1c, Fasting Glucose, Blood Pressure, Hemoglobin), 
and returns proposed structured observations for explicit patient confirmation.
"""

import os
import json
import re
import uuid
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import PatientDocument, Observation, Encounter, UserAccount
from backend.app.db.schemas import PatientDocumentRead
from backend.app.core.dependencies import get_current_user, verify_patient_access
from backend.app.core.security import decode_access_token
from backend.app.core.demo_users import DEMO_USERS_DB, User

DOCUMENTS_UPLOAD_DIR = Path("data/uploads/patient_documents")
DOCUMENTS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/documents", tags=["Patient Document Ingestion"])

# Supported file formats - arbitrary documents, images, tables, spreadsheets
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".csv", ".tsv", ".txt"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

def extract_text_from_file(file_path: Path, extension: str) -> str:
    """Extracts raw text from PDF, image, or text file using available parsing tools."""
    text_content = ""
    if extension in {".txt", ".text"}:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
        except Exception:
            text_content = ""
    elif extension == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
        except Exception as e:
            text_content = f"[PDF Parsing notice: Text layer could not be parsed automatically. Error: {str(e)}]"
    elif extension in {".png", ".jpg", ".jpeg"}:
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(str(file_path))
            text_content = pytesseract.image_to_string(img)
        except Exception:
            # Fallback when local OCR binary (tesseract) is not in PATH
            text_content = "[OCR notice: Scanned document stored securely. Optical Character Recognition awaiting confirmation.]"
    
    return text_content.strip()

def parse_medical_observations_from_text(text: str) -> List[Dict[str, Any]]:
    """Heuristic regex parser that detects standard lab markers from report text."""
    proposals = []
    
    # 1. Fasting Glucose / Blood Sugar
    fbs_match = re.search(r'(?:fasting\s+(?:blood\s+)?(?:glucose|sugar)|fbs)[\s:]*([0-9]{2,3}(?:\.[0-9]+)?)', text, re.IGNORECASE)
    if fbs_match:
        val = float(fbs_match.group(1))
        proposals.append({
            "test_code": "1558-6",
            "test_name": "Fasting glucose [Mass/volume] in Serum or Plasma",
            "value_numeric": val,
            "unit": "mg/dL",
            "reference_range": "70 - 99 mg/dL",
            "interpretation": "High" if val >= 100 else ("Normal" if val >= 70 else "Low")
        })

    # 2. HbA1c
    hba1c_match = re.search(r'(?:hba1c|glycated\s+hemoglobin|hemoglobin\s+a1c)[\s:]*([0-9]{1,2}(?:\.[0-9]+)?)\s*\%?', text, re.IGNORECASE)
    if hba1c_match:
        val = float(hba1c_match.group(1))
        proposals.append({
            "test_code": "4548-4",
            "test_name": "Hemoglobin A1c/Hemoglobin.total in Blood",
            "value_numeric": val,
            "unit": "%",
            "reference_range": "< 5.7 %",
            "interpretation": "High" if val >= 5.7 else "Normal"
        })

    # 3. Blood Pressure
    bp_match = re.search(r'(?:blood\s+pressure|bp)[\s:]*([0-9]{2,3})\s*[\/\-]\s*([0-9]{2,3})', text, re.IGNORECASE)
    if bp_match:
        sys_val = float(bp_match.group(1))
        dia_val = float(bp_match.group(2))
        proposals.append({
            "test_code": "8480-6",
            "test_name": "Systolic blood pressure",
            "value_numeric": sys_val,
            "unit": "mmHg",
            "reference_range": "90 - 120 mmHg",
            "interpretation": "High" if sys_val > 120 else "Normal"
        })
        proposals.append({
            "test_code": "8462-4",
            "test_name": "Diastolic blood pressure",
            "value_numeric": dia_val,
            "unit": "mmHg",
            "reference_range": "60 - 80 mmHg",
            "interpretation": "High" if dia_val > 80 else "Normal"
        })

    return proposals

@router.post("/upload", response_model=PatientDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_patient_document(
    patient_id: str = Form(...),
    document_type: str = Form("laboratory_report"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce patient authorization
    if current_user.role == "patient" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized patient access.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Secure storage path
    doc_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
    saved_filename = f"{patient_id}_{doc_id}{ext}"
    destination = DOCUMENTS_UPLOAD_DIR / saved_filename

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds maximum allowed 15 MB limit.")

    with open(destination, "wb") as f:
        f.write(contents)

    # Universal Multimodal Extraction & Auto-Append to EHR
    # Handles arbitrary structure, non-rigid naming, images, scans, CSVs, and PDFs
    from backend.app.services.universal_extractor import UniversalExtractorService
    extraction_result = UniversalExtractorService.process_and_append_document(
        file_path=destination,
        file_name=file.filename or saved_filename,
        patient_id=patient_id,
        db=db
    )
    extracted_data = extraction_result.get("extracted", {})
    appended_counts = extraction_result.get("appended", {})
    summary_text = extracted_data.get("document_summary", "")

    # Check if file is an image scan (MRI, CT, Ultrasound, X-ray)
    is_scan_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    imaging_analysis = None
    if is_scan_image:
        from backend.app.services.imaging_service import ImagingAnalysisService
        try:
            imaging_analysis = ImagingAnalysisService.analyze_scan_image(destination)
        except Exception as e:
            logger.warning(f"Imaging analysis failed: {e}")

    # Combine imaging analysis into extracted metadata
    if imaging_analysis and imaging_analysis.get("findings"):
        extracted_data["imaging_analysis"] = imaging_analysis
        if not summary_text:
            summary_text = imaging_analysis.get("overall_impression", "")

    doc_record = PatientDocument(
        document_id=doc_id,
        patient_id=patient_id,
        file_name=file.filename or saved_filename,
        file_type=ext.replace(".", ""),
        file_path=str(destination),
        file_size_bytes=len(contents),
        document_type="radiological_scan" if is_scan_image else document_type,
        report_date=date.today(),
        extracted_text=summary_text[:4000] if summary_text else None,
        extracted_metadata=json.dumps(extracted_data),
        confirmation_status="confirmed"
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    return PatientDocumentRead.model_validate(doc_record)

@router.post("/{document_id}/confirm", response_model=PatientDocumentRead)
def confirm_extracted_observations(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.scalar(select(PatientDocument).where(PatientDocument.document_id == document_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if current_user.role == "patient" and current_user.patient_id != doc.patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized patient access.")

    if doc.extracted_metadata:
        proposals = json.loads(doc.extracted_metadata)
        # Create an encounter anchor if needed
        enc_id = f"ENC-DOC-{doc.document_id}"
        existing_enc = db.scalar(select(Encounter).where(Encounter.encounter_id == enc_id))
        if not existing_enc:
            enc = Encounter(
                encounter_id=enc_id,
                patient_id=doc.patient_id,
                encounter_date=doc.report_date or date.today(),
                facility="Patient Uploaded Diagnostic Report",
                district="Diagnostic Lab",
                encounter_type="Diagnostic Report Extraction",
                attending_provider="Laboratory Specialist",
                is_synthetic=False
            )
            db.add(enc)
            db.flush()

        for p in proposals:
            obs = Observation(
                observation_id=f"OBS-{uuid.uuid4().hex[:8].upper()}",
                encounter_id=enc_id,
                patient_id=doc.patient_id,
                test_code=p.get("test_code", "CUSTOM-LAB"),
                test_name=p.get("test_name", "Extracted Observation"),
                value_numeric=p.get("value_numeric"),
                value_text=str(p.get("value_numeric", "")),
                unit=p.get("unit"),
                reference_range=p.get("reference_range"),
                interpretation=p.get("interpretation"),
                date=doc.report_date or date.today(),
                is_synthetic=False
            )
            db.add(obs)

    doc.confirmation_status = "confirmed"
    db.commit()
    db.refresh(doc)
    return PatientDocumentRead.model_validate(doc)

@router.get("/{document_id}/file")
def get_document_file(
    document_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(lambda: None)
):
    """Serve the raw medical document file (PDF, PNG, JPG, scan) for viewing or downloading."""
    # Resolve user from Bearer header or query token parameter (for direct browser <img> / <iframe> loads)
    authenticated_user: Optional[User] = None
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            sub = payload.get("sub")
            if sub in DEMO_USERS_DB:
                authenticated_user = DEMO_USERS_DB[sub]
            else:
                db_user = db.scalar(select(UserAccount).where((UserAccount.username == sub) | (UserAccount.email == sub)))
                if db_user:
                    authenticated_user = User(
                        username=db_user.username,
                        password_hash=db_user.password_hash,
                        role=db_user.role,
                        patient_id=db_user.patient_id,
                        full_name=db_user.full_name,
                        facility="Aarogya Patient Portal"
                    )

    doc = db.scalar(select(PatientDocument).where(PatientDocument.document_id == document_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if authenticated_user and authenticated_user.role == "patient" and authenticated_user.patient_id != doc.patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to patient document.")

    path = Path(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical document file missing on server storage.")

    media_type_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "csv": "text/csv",
        "txt": "text/plain"
    }
    media_type = media_type_map.get(doc.file_type.lower(), "application/octet-stream")

    return FileResponse(
        path=str(path),
        filename=doc.file_name,
        media_type=media_type,
        content_disposition_type="inline"  # Allows in-browser rendering for PDFs and Images
    )

