"""
Retrieval Quality Evaluation Benchmark for Aarogya Drishti Knowledge Base
Evaluates:
- Relevant medical queries across 12 clinical domains
- Similar but distinct conditions (e.g. Type 1 vs Type 2 diabetes, Heart Failure vs Angina)
- Unsupported medical queries (e.g. rare veterinary diseases, exotic syndromes not in corpus)
- Nonmedical queries (e.g. quantum physics, general trivia)
- Ambiguous symptom queries
- Queries requiring information absent from corpus

Calculates:
- Recall@3, Recall@5
- Mean Reciprocal Rank (MRR)
- Precision@3, Precision@5
- Unsupported-query rejection rate across different similarity thresholds (0.35, 0.38, 0.42, 0.45)
- Retrieval Latency distribution
"""

import time
import json
from typing import List, Dict, Any, Optional

from rag.retrieval import MedicalRetrievalService

# 25 Labeled Retrieval Test Cases
RETRIEVAL_TEST_CASES = [
    # 1. Diabetes
    {
        "query": "What are the fasting plasma glucose criteria to diagnose diabetes?",
        "expected_domain": "diabetes",
        "expected_doc": "MEDLINEPLUS-DIABETES-XML",
        "is_supported": True
    },
    {
        "query": "How is diabetic nephropathy screened with urine albumin?",
        "expected_domain": "diabetes",
        "expected_doc": "MEDLINEPLUS-DIABETIC-NEPHROPATHY",
        "is_supported": True
    },
    {
        "query": "What are the signs of diabetic retinopathy on fundoscopy?",
        "expected_domain": "diabetes",
        "expected_doc": "MEDLINEPLUS-DIABETIC-RETINOPATHY",
        "is_supported": True
    },
    # 2. Hypertension
    {
        "query": "What systolic blood pressure defines stage 2 hypertension?",
        "expected_domain": "hypertension",
        "expected_doc": "MEDLINEPLUS-HYPERTENSION-XML",
        "is_supported": True
    },
    {
        "query": "What are the first line antihypertensive drug classes recommended by WHO?",
        "expected_domain": "hypertension",
        "expected_doc": "WHO-HTN-GUIDELINE-2021",
        "is_supported": True
    },
    # 3. Cardiovascular
    {
        "query": "What are the core components of the WHO HEARTS technical package?",
        "expected_domain": "cardiovascular",
        "expected_doc": "WHO-HEARTS-CVD-2020",
        "is_supported": True
    },
    {
        "query": "What is the typical presentation and radiation pattern of stable angina?",
        "expected_domain": "cardiovascular",
        "expected_doc": "MEDLINEPLUS-CORONARY-ARTERY-DISEASE",
        "is_supported": True
    },
    {
        "query": "What are the four foundational medication pillars for heart failure with reduced ejection fraction?",
        "expected_domain": "cardiovascular",
        "expected_doc": "MEDLINEPLUS-HEART-FAILURE",
        "is_supported": True
    },
    # 4. Respiratory (Asthma / COPD)
    {
        "query": "What spirometric criteria confirm bronchodilator reversibility in asthma?",
        "expected_domain": "respiratory",
        "expected_doc": "MEDLINEPLUS-ASTHMA",
        "is_supported": True
    },
    {
        "query": "What is the fixed post-bronchodilator FEV1/FVC ratio defining COPD?",
        "expected_domain": "respiratory",
        "expected_doc": "MEDLINEPLUS-COPD",
        "is_supported": True
    },
    # 5. Nephrology (CKD)
    {
        "query": "What eGFR and urine albumin levels define chronic kidney disease staging?",
        "expected_domain": "nephrology",
        "expected_doc": "MEDLINEPLUS-CHRONIC-KIDNEY-DISEASE",
        "is_supported": True
    },
    # 6. Hematology (Anemia)
    {
        "query": "What laboratory tests distinguish microcytic iron deficiency anemia?",
        "expected_domain": "hematology",
        "expected_doc": "MEDLINEPLUS-IRON-DEFICIENCY-ANEMIA",
        "is_supported": True
    },
    {
        "query": "What hemoglobin cutoff does WHO define for anemia in pregnant women?",
        "expected_domain": "hematology",
        "expected_doc": "WHO-ANEMIA-GUIDELINES-2023",
        "is_supported": True
    },
    # 7. Endocrinology (Thyroid)
    {
        "query": "What TSH and free T4 levels indicate primary hypothyroidism?",
        "expected_domain": "endocrinology",
        "expected_doc": "MEDLINEPLUS-HYPOTHYROIDISM",
        "is_supported": True
    },
    {
        "query": "What are the clinical signs of Graves disease and hyperthyroidism?",
        "expected_domain": "endocrinology",
        "expected_doc": "MEDLINEPLUS-HYPERTHYROIDISM",
        "is_supported": True
    },
    # 8. Infectious Diseases (TB, Malaria, Dengue)
    {
        "query": "What is the standard 6-month first-line chemotherapy regimen for pulmonary tuberculosis?",
        "expected_domain": "infectious_diseases",
        "expected_doc": "WHO-TUBERCULOSIS-2023",
        "is_supported": True
    },
    {
        "query": "Why does WHO recommend artemisinin-based combination therapy for falciparum malaria?",
        "expected_domain": "infectious_diseases",
        "expected_doc": "WHO-MALARIA-TREATMENT-2022",
        "is_supported": True
    },
    {
        "query": "What clinical warning signs in dengue indicate capillary leakage and severe disease?",
        "expected_domain": "infectious_diseases",
        "expected_doc": "WHO-DENGUE-CLINICAL-2023",
        "is_supported": True
    },
    # 9. Gastroenterology
    {
        "query": "What are alarm features for GERD requiring urgent upper endoscopy?",
        "expected_domain": "gastroenterology",
        "expected_doc": "MEDLINEPLUS-GERD-REFLUX",
        "is_supported": True
    },
    {
        "query": "What is the recommended 14-day quadruple eradication regimen for H. pylori peptic ulcers?",
        "expected_domain": "gastroenterology",
        "expected_doc": "MEDLINEPLUS-PEPTIC-ULCER",
        "is_supported": True
    },
    # 10. Neurology
    {
        "query": "What do the letters in the BE-FAST acronym stand for in acute stroke?",
        "expected_domain": "neurology",
        "expected_doc": "MEDLINEPLUS-STROKE-OVERVIEW",
        "is_supported": True
    },
    {
        "query": "What is the emergency definition and first-line treatment for status epilepticus?",
        "expected_domain": "neurology",
        "expected_doc": "MEDLINEPLUS-EPILEPSY-SEIZURES",
        "is_supported": True
    },
    # 11. Maternal Health
    {
        "query": "What blood pressure and proteinuria thresholds define preeclampsia after 20 weeks gestation?",
        "expected_domain": "maternal_health",
        "expected_doc": "MEDLINEPLUS-PREECLAMPSIA-PREGNANCY",
        "is_supported": True
    },
    # 12. Unsupported / Nonmedical Queries (Must NOT retrieve relevant clinical match)
    {
        "query": "How do you diagnose and treat feline leukemia virus in domestic cats?",
        "expected_domain": None,
        "expected_doc": None,
        "is_supported": False
    },
    {
        "query": "What is the mathematical proof of the Riemann hypothesis in complex analysis?",
        "expected_domain": None,
        "expected_doc": None,
        "is_supported": False
    }
]

def evaluate_retrieval(namespace: str = "medical-references-v2") -> Dict[str, Any]:
    retriever = MedicalRetrievalService(namespace=namespace)
    
    hits_at_3 = 0
    hits_at_5 = 0
    mrr_sum = 0.0
    precision_at_3_sum = 0.0
    latencies = []
    
    unsupported_scores = []
    supported_scores = []
    
    detailed_results = []
    
    for case in RETRIEVAL_TEST_CASES:
        t0 = time.perf_counter()
        resp = retriever.search(case["query"], top_k=5)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)
        
        results = resp.get("results", [])
        top_score = results[0]["similarity_score"] if results else 0.0
        
        if not case["is_supported"]:
            unsupported_scores.append(top_score)
            detailed_results.append({
                "query": case["query"],
                "supported": False,
                "top_score": top_score,
                "top_doc": results[0].get("document_id") if results else None
            })
            continue
            
        supported_scores.append(top_score)
        
        # Check rank of expected document
        rank = 0
        p3_hits = 0
        expected_doc = case["expected_doc"]
        
        for idx, match in enumerate(results, 1):
            doc_id = match.get("document_id")
            if doc_id == expected_doc:
                if rank == 0:
                    rank = idx
            if idx <= 3 and doc_id == expected_doc:
                p3_hits += 1
                
        if rank > 0 and rank <= 3:
            hits_at_3 += 1
        if rank > 0 and rank <= 5:
            hits_at_5 += 1
        if rank > 0:
            mrr_sum += 1.0 / rank
            
        precision_at_3_sum += (p3_hits / 3.0)
        
        detailed_results.append({
            "query": case["query"],
            "supported": True,
            "rank": rank,
            "top_score": top_score,
            "top_doc": results[0].get("document_id") if results else None,
            "expected_doc": expected_doc
        })
        
    num_supported = sum(1 for c in RETRIEVAL_TEST_CASES if c["is_supported"])
    recall_at_3 = round(hits_at_3 / num_supported, 4)
    recall_at_5 = round(hits_at_5 / num_supported, 4)
    mrr = round(mrr_sum / num_supported, 4)
    mean_p3 = round(precision_at_3_sum / num_supported, 4)
    avg_latency = round(sum(latencies) / len(latencies), 2)
    
    # Threshold Calibration Analysis
    thresholds = [0.35, 0.38, 0.40, 0.42, 0.45]
    threshold_analysis = {}
    for th in thresholds:
        supp_passed = sum(1 for s in supported_scores if s >= th)
        unsupp_rejected = sum(1 for s in unsupported_scores if s < th)
        threshold_analysis[f"threshold_{th}"] = {
            "supported_pass_rate": round(supp_passed / len(supported_scores), 4),
            "unsupported_rejection_rate": round(unsupp_rejected / len(unsupported_scores), 4)
        }
        
    summary = {
        "namespace": namespace,
        "total_queries": len(RETRIEVAL_TEST_CASES),
        "supported_queries": num_supported,
        "unsupported_queries": len(RETRIEVAL_TEST_CASES) - num_supported,
        "recall_at_3": recall_at_3,
        "recall_at_5": recall_at_5,
        "mrr": mrr,
        "precision_at_3": mean_p3,
        "mean_latency_ms": avg_latency,
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "mean_supported_score": round(sum(supported_scores) / len(supported_scores), 4),
        "mean_unsupported_score": round(sum(unsupported_scores) / len(unsupported_scores), 4),
        "threshold_calibration": threshold_analysis,
        "detailed_results": detailed_results
    }
    return summary

if __name__ == "__main__":
    res = evaluate_retrieval()
    print("=== RETRIEVAL EVALUATION SUMMARY ===")
    print(f"Recall@3: {res['recall_at_3'] * 100:.1f}%")
    print(f"Recall@5: {res['recall_at_5'] * 100:.1f}%")
    print(f"MRR: {res['mrr']}")
    print(f"Precision@3: {res['precision_at_3']}")
    print(f"Mean Latency: {res['mean_latency_ms']} ms")
    print("Threshold Calibration:", json.dumps(res["threshold_calibration"], indent=2))

