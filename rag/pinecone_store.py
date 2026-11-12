"""
Pinecone Vector Store Integration for Aarogya-Drishti EHR
Using Pinecone Modern SDK:
- Dimension: 384
- Metric: cosine
- Serverless deployment (aws/us-east-1 by default or env configurable)
- Namespace: medical-references-v1
- Strict isolation: NEVER mixes identifiable patient EHR data with reference knowledge
- Strict error raising: Missing credentials or connection failures raise explicit RuntimeError/ValueError
  (Automatic simulation fallback is disabled unless explicitly requested via use_mock=True for local unit testing).
"""

import os
import time
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv("backend/.env")

DEFAULT_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "aarogya-medical-knowledge")
DEFAULT_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "medical-references-v1")
EXPECTED_DIMENSION = 384

class MockPineconeIndex:
    """In-memory vector store simulator strictly for offline unit testing."""

    def __init__(self, name: str, dimension: int = 384, metric: str = "cosine"):
        self.name = name
        self.dimension = dimension
        self.metric = metric
        self.namespaces: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def describe_index_stats(self):
        total_count = sum(len(records) for records in self.namespaces.values())
        return {
            "dimension": self.dimension,
            "total_vector_count": total_count,
            "namespaces": {ns: {"vector_count": len(recs)} for ns, recs in self.namespaces.items()}
        }

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = DEFAULT_NAMESPACE):
        if namespace not in self.namespaces:
            self.namespaces[namespace] = {}
        for vec in vectors:
            v_id = vec["id"]
            values = vec["values"]
            metadata = vec.get("metadata", {})
            self.namespaces[namespace][v_id] = {
                "id": v_id,
                "values": values,
                "metadata": metadata
            }
        return {"upserted_count": len(vectors)}

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: str = DEFAULT_NAMESPACE,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ):
        ns_records = self.namespaces.get(namespace, {})
        if not ns_records:
            return {"matches": []}

        import numpy as np
        q_vec = np.array(vector, dtype=float)
        norm_q = np.linalg.norm(q_vec) or 1.0

        matches = []
        for v_id, record in ns_records.items():
            meta = record.get("metadata", {})
            if filter:
                match_filter = True
                for k, v in filter.items():
                    if meta.get(k) != v:
                        match_filter = False
                        break
                if not match_filter:
                    continue

            d_vec = np.array(record["values"], dtype=float)
            norm_d = np.linalg.norm(d_vec) or 1.0
            score = float(np.dot(q_vec, d_vec) / (norm_q * norm_d))
            matches.append({
                "id": v_id,
                "score": score,
                "metadata": meta if include_metadata else {}
            })

        matches.sort(key=lambda m: m["score"], reverse=True)
        return {"matches": matches[:top_k]}

    def delete(self, ids: Optional[List[str]] = None, delete_all: bool = False, namespace: str = DEFAULT_NAMESPACE):
        if namespace not in self.namespaces:
            return
        if delete_all:
            self.namespaces[namespace].clear()
        elif ids:
            for v_id in ids:
                self.namespaces[namespace].pop(v_id, None)

class PineconeManager:

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: str = None,
        dimension: int = EXPECTED_DIMENSION,
        cloud: str = "aws",
        region: str = "us-east-1",
        use_mock: bool = False
    ):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", DEFAULT_INDEX_NAME)
        self.dimension = dimension
        self.cloud = cloud
        self.region = region
        self.use_mock = use_mock
        self.client: Optional[Pinecone] = None
        self._index = None

        if self.use_mock:
            print("[INFO] Initializing PineconeManager in explicit Mock mode.")
            self._index = MockPineconeIndex(name=self.index_name, dimension=self.dimension)
            return

        # Explicit verification: missing API key must raise error, not silently fall back
        if not self.api_key:
            raise ValueError(
                "Missing PINECONE_API_KEY. Set it in .env or pass it to PineconeManager. "
                "Automatic fallback to mock simulation is disabled."
            )

        try:
            self.client = Pinecone(api_key=self.api_key)
            self._init_index()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Pinecone service: {str(e)}") from e

    def _init_index(self):
        existing_indexes = [idx["name"] for idx in self.client.list_indexes()]
        if self.index_name not in existing_indexes:
            print(f"[INFO] Index '{self.index_name}' not found. Creating serverless index (cloud={self.cloud}, region={self.region}, dimension={self.dimension})...")
            self.client.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=self.cloud, region=self.region)
            )
            # Wait for readiness
            print("[INFO] Waiting for Pinecone index to be ready...")
            while not self.client.describe_index(self.index_name).status["ready"]:
                time.sleep(2)
            print(f"[INFO] Index '{self.index_name}' created and ready.")

        # Validate configuration
        desc = self.client.describe_index(self.index_name)
        if desc.dimension != self.dimension:
            raise ValueError(
                f"Pinecone index dimension mismatch: Index has {desc.dimension}, but pipeline requires {self.dimension}"
            )
        if desc.metric != "cosine":
            raise ValueError(
                f"Pinecone index metric mismatch: Index has {desc.metric}, but pipeline requires cosine"
            )
        self._index = self.client.Index(self.index_name)

    def get_index(self):
        return self._index
