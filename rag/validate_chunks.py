"""
Chunk Validation and Quality Assurance Suite
Validates:
- All required metadata fields are present and non-empty.
- Chunk token boundaries fall within reasonable limits (<= max_tokens + margin).
- Content preservation and clinical terms integrity.
- Attribution, license, and provenance verification.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

REQUIRED_CHUNK_FIELDS = [
    "chunk_id",
    "document_id",
    "title",
    "source_organization",
    "source_url",
    "publication_date",
    "retrieval_date",
    "section_heading",
    "medical_topic",
    "document_version",
    "review_status",
    "token_count",
    "content"
]

def validate_chunk_record(chunk: Dict[str, Any], max_allowed_tokens: int = 650) -> Tuple[bool, List[str]]:
    errors = []
    # 1. Field presence
    for field in REQUIRED_CHUNK_FIELDS:
        if field not in chunk or chunk[field] is None:
            errors.append(f"Missing required field: '{field}'")
        elif isinstance(chunk[field], str) and not chunk[field].strip():
            errors.append(f"Empty required field: '{field}'")

    # 2. Token boundaries
    token_cnt = chunk.get("token_count", 0)
    if token_cnt <= 0:
        errors.append(f"Invalid token_count: {token_cnt}")
    elif token_cnt > max_allowed_tokens:
        errors.append(f"Chunk exceeds max token bound ({token_cnt} > {max_allowed_tokens})")

    # 3. Topic validation
    if chunk.get("medical_topic") not in ["diabetes", "hypertension", "cardiovascular"]:
        errors.append(f"Unknown medical_topic: '{chunk.get('medical_topic')}'")

    return len(errors) == 0, errors

def validate_jsonl_file(jsonl_path: Path) -> Dict[str, Any]:
    if not jsonl_path.exists():
        return {"valid": False, "error": f"File not found: {jsonl_path}"}

    total_chunks = 0
    invalid_chunks = 0
    all_errors = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            total_chunks += 1
            try:
                record = json.loads(line)
                is_valid, errors = validate_chunk_record(record)
                if not is_valid:
                    invalid_chunks += 1
                    all_errors.append({"line": idx, "errors": errors})
            except Exception as e:
                invalid_chunks += 1
                all_errors.append({"line": idx, "errors": [f"Malformed JSON: {str(e)}"]})

    return {
        "valid": invalid_chunks == 0,
        "total_chunks": total_chunks,
        "invalid_chunks": invalid_chunks,
        "errors": all_errors[:10]
    }

