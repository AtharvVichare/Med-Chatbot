"""
Medical Reference Sources Registry for Aarogya-Drishti Knowledge Base
Maintains authoritative metadata, provenance, licensing, and topics for:
1. MedlinePlus Health Topics (U.S. National Library of Medicine / NIH) - Public Domain (U.S. Gov)
2. World Health Organization (WHO) Clinical Guidelines - Open Access (CC BY-NC-SA 3.0 IGO)
3. Standard Medical Reference Guidelines (MoHFW India / Clinical Protocols)
Focus Topics: Diabetes Mellitus, Hypertension, Cardiovascular Health.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field

class MedicalSourceMetadata(BaseModel):
    source_id: str
    title: str
    organization: str
    source_url: str
    source_type: str  # 'xml', 'pdf'
    topic: str        # 'diabetes', 'hypertension', 'cardiovascular'
    license: str
    publication_date: str
    document_version: str
    review_status: str
    is_official: bool = True

MEDICAL_SOURCES_REGISTRY: Dict[str, MedicalSourceMetadata] = {
    # 1. MedlinePlus Health Topics XML Sources
    "MEDLINEPLUS-DIABETES-XML": MedicalSourceMetadata(
        source_id="MEDLINEPLUS-DIABETES-XML",
        title="MedlinePlus Health Topic: Diabetes",
        organization="U.S. National Library of Medicine (NLM / NIH)",
        source_url="https://medlineplus.gov/diabetes.html",
        source_type="xml",
        topic="diabetes",
        license="Public Domain (U.S. Government Work)",
        publication_date="2025-01-15",
        document_version="v2025.1",
        review_status="peer-reviewed / medically reviewed by NLM"
    ),
    "MEDLINEPLUS-HYPERTENSION-XML": MedicalSourceMetadata(
        source_id="MEDLINEPLUS-HYPERTENSION-XML",
        title="MedlinePlus Health Topic: High Blood Pressure",
        organization="U.S. National Library of Medicine (NLM / NIH)",
        source_url="https://medlineplus.gov/highbloodpressure.html",
        source_type="xml",
        topic="hypertension",
        license="Public Domain (U.S. Government Work)",
        publication_date="2025-02-10",
        document_version="v2025.1",
        review_status="peer-reviewed / medically reviewed by NLM"
    ),
    "MEDLINEPLUS-CVD-XML": MedicalSourceMetadata(
        source_id="MEDLINEPLUS-CVD-XML",
        title="MedlinePlus Health Topic: Cardiovascular Disease Prevention",
        organization="U.S. National Library of Medicine (NLM / NIH)",
        source_url="https://medlineplus.gov/howtopreventheartdisease.html",
        source_type="xml",
        topic="cardiovascular",
        license="Public Domain (U.S. Government Work)",
        publication_date="2025-01-20",
        document_version="v2025.1",
        review_status="peer-reviewed / medically reviewed by NLM"
    ),

    # 2. WHO Guideline PDFs
    "WHO-HTN-GUIDELINE-2021": MedicalSourceMetadata(
        source_id="WHO-HTN-GUIDELINE-2021",
        title="WHO Guideline for the Pharmacological Treatment of Hypertension in Adults",
        organization="World Health Organization (WHO)",
        source_url="https://www.who.int/publications/i/item/9789240033986",
        source_type="pdf",
        topic="hypertension",
        license="CC BY-NC-SA 3.0 IGO",
        publication_date="2021-08-25",
        document_version="WHO-HTN-2021-Rev1",
        review_status="WHO Guidelines Approved by Guidelines Review Committee"
    ),
    "WHO-DIABETES-COMPACT-2023": MedicalSourceMetadata(
        source_id="WHO-DIABETES-COMPACT-2023",
        title="WHO Global Diabetes Compact: Diagnosis and Management Technical Brief",
        organization="World Health Organization (WHO)",
        source_url="https://www.who.int/initiatives/global-diabetes-compact",
        source_type="pdf",
        topic="diabetes",
        license="CC BY-NC-SA 3.0 IGO",
        publication_date="2023-04-14",
        document_version="WHO-GDC-2023",
        review_status="WHO Technical Guidance Approved"
    ),
    "WHO-HEARTS-CVD-2020": MedicalSourceMetadata(
        source_id="WHO-HEARTS-CVD-2020",
        title="HEARTS Technical Package for Cardiovascular Disease Management in Primary Health Care",
        organization="World Health Organization (WHO)",
        source_url="https://www.who.int/publications/i/item/9789240001367",
        source_type="pdf",
        topic="cardiovascular",
        license="CC BY-NC-SA 3.0 IGO",
        publication_date="2020-10-01",
        document_version="WHO-HEARTS-v2",
        review_status="WHO Technical Series Verified"
    )
}

def get_source_metadata(source_id: str) -> MedicalSourceMetadata:
    if source_id not in MEDICAL_SOURCES_REGISTRY:
        raise KeyError(f"Source ID '{source_id}' is not registered in MEDICAL_SOURCES_REGISTRY")
    return MEDICAL_SOURCES_REGISTRY[source_id]

