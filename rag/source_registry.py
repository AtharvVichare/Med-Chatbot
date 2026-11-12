"""
Comprehensive Medical Source Registry for Aarogya Drishti 2.0.
Tracks sources across:
- WHO publications
- MedlinePlus
- Gale Encyclopedia of Medicine
- MoHFW / National Health Mission / ICMR
- CDC public health references
- NICE / NCBI Bookshelf
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

REGISTRY_FILE = "data/reference/source_registry.json"

DEFAULT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "GALE-ENCYC-MED-3RD": {
        "document_id": "GALE-ENCYC-MED-3RD",
        "title": "The Gale Encyclopedia of Medicine",
        "publisher": "Gale Cengage Learning",
        "edition": "Third Edition",
        "original_url": "https://www.cengage.com/gale",
        "publication_date": "2006",
        "updated_date": "2006",
        "topic": "comprehensive_medicine",
        "subtopic": "clinical_encyclopedia",
        "document_type": "encyclopedia",
        "licence": "Educational & Clinical Reference Use",
        "source_version": "3.0",
        "source_path": "data/reference/guidelines/gale_encyclopedia_of_medicine_3rd_ed.pdf",
        "page_count": 4505,
        "format": "PDF",
        "ingestion_status": "READY_FOR_VECTORIZATION",
        "target_namespace": "medical-encyclopedia-v1"
    },
    "WHO-HTN-GUIDELINE-2021": {
        "document_id": "WHO-HTN-GUIDELINE-2021",
        "title": "Guideline for the Pharmacological Treatment of Hypertension in Adults",
        "publisher": "World Health Organization",
        "edition": "2021 Guidelines",
        "original_url": "https://www.who.int/publications/i/item/9789240033986",
        "publication_date": "2021-08-25",
        "updated_date": "2021-08-25",
        "topic": "cardiovascular",
        "subtopic": "hypertension",
        "document_type": "clinical_guideline",
        "licence": "CC BY-NC-SA 3.0 IGO",
        "source_version": "1.0",
        "source_path": "data/reference/guidelines/who_hypertension_guideline_2021.pdf",
        "page_count": 76,
        "format": "PDF",
        "ingestion_status": "INDEXED",
        "target_namespace": "medical-references-v2"
    },
    "WHO-HEARTS-CVD-2020": {
        "document_id": "WHO-HEARTS-CVD-2020",
        "title": "HEARTS Technical Package for Cardiovascular Disease Management in Primary Health Care",
        "publisher": "World Health Organization",
        "edition": "HEARTS 2020",
        "original_url": "https://www.who.int/publications/i/item/9789240001367",
        "publication_date": "2020-04-12",
        "updated_date": "2020-04-12",
        "topic": "cardiovascular",
        "subtopic": "primary_prevention",
        "document_type": "technical_package",
        "licence": "CC BY-NC-SA 3.0 IGO",
        "source_version": "1.0",
        "source_path": "data/reference/guidelines/who_hearts_cvd_package.pdf",
        "page_count": 48,
        "format": "PDF",
        "ingestion_status": "INDEXED",
        "target_namespace": "medical-references-v2"
    },
    "MEDLINEPLUS-DIABETES-XML": {
        "document_id": "MEDLINEPLUS-DIABETES-XML",
        "title": "MedlinePlus Clinical Reference: Diabetes Mellitus",
        "publisher": "National Library of Medicine (NIH)",
        "edition": "2023 Digital Edition",
        "original_url": "https://medlineplus.gov/diabetes.html",
        "publication_date": "2023-01-15",
        "updated_date": "2023-06-01",
        "topic": "diabetes",
        "subtopic": "type2_diabetes",
        "document_type": "consumer_health",
        "licence": "Public Domain (U.S. Government)",
        "source_version": "2.0",
        "source_path": "data/reference/xml/MEDLINEPLUS-DIABETES-XML.xml",
        "page_count": 1,
        "format": "XML",
        "ingestion_status": "INDEXED",
        "target_namespace": "medical-references-v2"
    },
    "MEDLINEPLUS-ASTHMA": {
        "document_id": "MEDLINEPLUS-ASTHMA",
        "title": "MedlinePlus Clinical Reference: Asthma Overview & Management",
        "publisher": "National Library of Medicine (NIH)",
        "edition": "2023 Digital Edition",
        "original_url": "https://medlineplus.gov/asthma.html",
        "publication_date": "2023-02-10",
        "updated_date": "2023-05-15",
        "topic": "respiratory",
        "subtopic": "asthma",
        "document_type": "consumer_health",
        "licence": "Public Domain (U.S. Government)",
        "source_version": "2.0",
        "source_path": "data/reference/xml/MEDLINEPLUS-ASTHMA.xml",
        "page_count": 1,
        "format": "XML",
        "ingestion_status": "INDEXED",
        "target_namespace": "medical-references-v2"
    },
    "MOHFW-EMERGENCY-TRIAGE-2022": {
        "document_id": "MOHFW-EMERGENCY-TRIAGE-2022",
        "title": "Clinical Protocols for Emergency & Acute Medical Triage",
        "publisher": "Ministry of Health and Family Welfare, Government of India",
        "edition": "2022 National Protocol",
        "original_url": "https://mohfw.gov.in",
        "publication_date": "2022-09-10",
        "updated_date": "2022-09-10",
        "topic": "emergency_medicine",
        "subtopic": "triage_and_stabilization",
        "document_type": "national_clinical_protocol",
        "licence": "Open Government Data (OGD) India",
        "source_version": "1.0",
        "source_path": "data/reference/xml/MOHFW-EMERGENCY-TRIAGE-2022.xml",
        "page_count": 1,
        "format": "XML",
        "ingestion_status": "INDEXED",
        "target_namespace": "medical-references-v2"
    }
}

class MedicalSourceRegistry:
    def __init__(self, registry_path: str = REGISTRY_FILE):
        self.registry_path = registry_path
        self.registry = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Initialize default and save
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        self._save(DEFAULT_REGISTRY)
        return DEFAULT_REGISTRY

    def _save(self, data: Dict[str, Dict[str, Any]]):
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register_source(self, metadata: Dict[str, Any]):
        doc_id = metadata["document_id"]
        # Compute file checksum if source_path exists
        sp = metadata.get("source_path")
        if sp and os.path.exists(sp):
            h = hashlib.sha256()
            with open(sp, "rb") as bf:
                while chunk := bf.read(65536):
                    h.update(chunk)
            metadata["checksum"] = h.hexdigest()
        metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.registry[doc_id] = metadata
        self._save(self.registry)

    def get_source(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self.registry.get(document_id)

    def list_sources(self) -> List[Dict[str, Any]]:
        return list(self.registry.values())

    def update_ingestion_status(self, document_id: str, status: str, vector_count: Optional[int] = None):
        if document_id in self.registry:
            self.registry[document_id]["ingestion_status"] = status
            if vector_count is not None:
                self.registry[document_id]["vector_count"] = vector_count
            self.registry[document_id]["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save(self.registry)

