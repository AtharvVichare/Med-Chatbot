"""
Document Manifest Manager for Aarogya-Drishti Medical RAG
Tracks:
- Document registration, hashes, extraction status
- Chunk count and output artifact references
- Document failures and processing timestamps
- Verification of checksums for duplicate prevention
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "documents_manifest.json"

def calculate_checksum(file_path: Path) -> str:
    """Computes SHA-256 checksum of document content."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

class DocumentManifest:

    def __init__(self, manifest_path: Path = MANIFEST_PATH):
        self.manifest_path = manifest_path
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "documents": {},
            "summary": {
                "total_documents": 0,
                "successful_documents": 0,
                "failed_documents": 0,
                "total_chunks": 0
            }
        }

    def save(self):
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        successful = sum(1 for d in self.data["documents"].values() if d["status"] == "SUCCESS")
        failed = sum(1 for d in self.data["documents"].values() if d["status"] == "FAILED")
        chunks = sum(d.get("chunk_count", 0) for d in self.data["documents"].values())
        
        self.data["summary"] = {
            "total_documents": len(self.data["documents"]),
            "successful_documents": successful,
            "failed_documents": failed,
            "total_chunks": chunks
        }
        
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def is_duplicate_hash(self, sha256_hash: str) -> Optional[str]:
        for doc_id, doc in self.data["documents"].items():
            if doc.get("sha256") == sha256_hash:
                return doc_id
        return None

    def record_document(
        self,
        document_id: str,
        title: str,
        source_id: str,
        file_path: str,
        sha256: str,
        status: str,
        chunk_count: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.data["documents"][document_id] = {
            "document_id": document_id,
            "title": title,
            "source_id": source_id,
            "file_path": str(file_path),
            "sha256": sha256,
            "status": status,
            "chunk_count": chunk_count,
            "error_message": error_message,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        self.save()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self.data["documents"].get(document_id)

