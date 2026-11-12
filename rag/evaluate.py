"""
Retrieval Benchmark and Evaluation Suite
Evaluates semantic retrieval across:
- Diabetes
- Hypertension
- Cardiovascular health
- Out-of-domain questions (unrelated or non-indexed questions)

Calculates:
- Recall@3
- Recall@5
- Mean Reciprocal Rank (MRR)
- Average query latency (ms)
Uses verified medical query ground-truth labels.
"""

import time
from typing import List, Dict, Any
from rag.retrieval import MedicalRetrievalService
from rag.vector_upsert import VectorIndexer

# Ground truth evaluation dataset
EVALUATION_DATASET = [
    {
        "query": "What are the diagnostic blood glucose and HbA1c criteria for diabetes?",
        "topic": "diabetes",
        "expected_topic": "diabetes",
        "relevant_doc_id": "MEDLINEPLUS-DIABETES-XML",
        "expected_keywords": ["HbA1c", "126 mg/dL", "Fasting"]
    },
    {
        "query": "What are the recommended first-line blood pressure medications according to WHO guidelines?",
        "topic": "hypertension",
        "expected_topic": "hypertension",
        "relevant_doc_id": "WHO-HTN-GUIDELINE-2021",
        "expected_keywords": ["Amlodipine", "diuretics", "140/90"]
    },
    {
        "query": "What lifestyle modifications and salt reduction are recommended for cardiovascular disease prevention?",
        "topic": "cardiovascular",
        "expected_topic": "cardiovascular",
        "relevant_doc_id": "WHO-HEARTS-CVD-2020",
        "expected_keywords": ["salt", "lifestyle", "trans-fats"]
    },
    {
        "query": "What blood pressure thresholds define stage 1 and stage 2 hypertension?",
        "topic": "hypertension",
        "expected_topic": "hypertension",
        "relevant_doc_id": "MEDLINEPLUS-HYPERTENSION-XML",
        "expected_keywords": ["130-139", "140", "Stage 1"]
    },
    {
        "query": "How is diabetic ketoacidosis managed in veterinary feline patients?",
        "topic": "out_of_domain",
        "expected_topic": None,
        "relevant_doc_id": None,
        "expected_keywords": []
    }
]

def evaluate_retrieval(service: MedicalRetrievalService) -> Dict[str, Any]:
    r3_hits = 0
    r5_hits = 0
    reciprocal_ranks = []
    latencies = []
    detailed_results = []

    domain_queries = [item for item in EVALUATION_DATASET if item["expected_topic"] is not None]

    for item in EVALUATION_DATASET:
        t0 = time.perf_counter()
        resp = service.search(query=item["query"], top_k=5)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        results = resp.get("results", [])
        
        # Out of domain check
        if item["expected_topic"] is None:
            # Check maximum similarity score for out-of-domain
            top_score = results[0]["similarity_score"] if results else 0.0
            detailed_results.append({
                "query": item["query"],
                "type": "out_of_domain",
                "top_similarity": top_score,
                "passed": top_score < 0.65
            })
            continue

        target_doc = item["relevant_doc_id"]
        matched_rank = None
        for rank, r in enumerate(results, start=1):
            chunk_doc = r.get("citation", "")
            # Check if relevant keywords or doc appear
            if any(kw.lower() in r["content"].lower() for kw in item["expected_keywords"]):
                matched_rank = rank
                break

        if matched_rank is not None:
            reciprocal_ranks.append(1.0 / matched_rank)
            if matched_rank <= 3:
                r3_hits += 1
            if matched_rank <= 5:
                r5_hits += 1
        else:
            reciprocal_ranks.append(0.0)

        detailed_results.append({
            "query": item["query"],
            "matched_rank": matched_rank,
            "top_citation": results[0]["citation"] if results else None,
            "top_score": results[0]["similarity_score"] if results else 0.0,
            "latency_ms": round(lat, 2)
        })

    n = len(domain_queries)
    metrics = {
        "total_domain_queries": n,
        "recall_at_3": round(r3_hits / n, 4) if n else 0.0,
        "recall_at_5": round(r5_hits / n, 4) if n else 0.0,
        "mean_reciprocal_rank": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else 0.0,
        "avg_query_latency_ms": round(sum(latencies) / len(latencies), 2),
        "evaluation_details": detailed_results
    }
    return metrics

if __name__ == "__main__":
    print("Running vector indexing and semantic retrieval benchmark...")
    indexer = VectorIndexer()
    indexer.index_all_processed()
    retriever = MedicalRetrievalService()
    report = evaluate_retrieval(retriever)
    import json
    print(json.dumps(report, indent=2))

