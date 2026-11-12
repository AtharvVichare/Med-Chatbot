import os
import sys
import time
import json
from dotenv import load_dotenv

load_dotenv(".env")
sys.path.insert(0, ".")

from rag.pinecone_store import PineconeManager
from rag.vector_upsert import VectorIndexer
from rag.retrieval import MedicalRetrievalService

print("=" * 80)
print("AAROGYA DRISHTI 2.0 - LIVE PINECONE VERIFICATION")
print("=" * 80)

# 1. Connect & Create Index
print("\n[STEP 1] Connecting to Pinecone serverless service...")
pm = PineconeManager()
index = pm.get_index()

# 2. Check Index Configuration
desc = pm.client.describe_index(pm.index_name)
print(f"Index Name: {desc.name}")
print(f"Dimension:  {desc.dimension} (Expected: 384)")
print(f"Metric:     {desc.metric} (Expected: cosine)")
print(f"Host:       {desc.host}")
print(f"Status:     {desc.status.get('state', 'ready')}")

# 3. Vector Upsert (Batch 1)
print("\n[STEP 2] Upserting 9 validated medical reference chunks into 'medical-references-v1'...")
indexer = VectorIndexer(pinecone_manager=pm)
upsert_1 = indexer.index_all_processed()
print("First upsert summary:", json.dumps(upsert_1["files"], indent=2))
print(f"Total vectors sent: {upsert_1['total_vectors_indexed']}")

# 4. Eventual Consistency Polling
print("\n[STEP 3] Polling Pinecone index statistics for remote vector count...")
for attempt in range(1, 10):
    time.sleep(3)
    stats = index.describe_index_stats()
    ns_info = stats.get("namespaces", {}).get("medical-references-v1", {})
    count = ns_info.get("vector_count", 0)
    print(f"   Attempt {attempt}: Remote vector count in 'medical-references-v1' = {count}")
    if count >= 9:
        break

# 5. Verify Idempotency (Batch 2)
print("\n[STEP 4] Testing Idempotency (repeating exact upload)...")
upsert_2 = indexer.index_all_processed()
time.sleep(3)
stats_after = index.describe_index_stats()
ns_count_after = stats_after.get("namespaces", {}).get("medical-references-v1", {}).get("vector_count", 0)
print(f"Remote vector count after re-upload: {ns_count_after}")
assert ns_count_after == 9, f"Idempotency violation! Expected 9 vectors, found {ns_count_after}"
print("IDEMPOTENCY CONFIRMED: Vector count remained exactly 9 without duplicate records.")

# 6. Execute 5 Real Semantic Retrieval Queries
queries = [
    "What are the diagnostic blood glucose and HbA1c criteria for diabetes?",
    "What are the recommended first-line blood pressure medications according to WHO guidelines?",
    "What blood pressure thresholds define stage 1 and stage 2 hypertension?",
    "What lifestyle modifications and salt reduction are recommended for cardiovascular disease prevention?",
    "What are the symptoms and complications of untreated high blood sugar?"
]

print("\n[STEP 5] Executing 5 Real Semantic Retrieval Queries against Pinecone:")
print("-" * 80)
retriever = MedicalRetrievalService(pinecone_manager=pm)

latencies = []
for idx, q in enumerate(queries, start=1):
    t0 = time.perf_counter()
    res = retriever.search(query=q, top_k=2)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    latencies.append(elapsed_ms)

    top_hit = res["results"][0] if res["results"] else {}
    print(f"\nQuery #{idx}: \"{q}\"")
    print(f"   Latency:    {elapsed_ms:.2f} ms (E2E network + embedding)")
    print(f"   Top Score:  {top_hit.get('similarity_score')}")
    print(f"   Chunk ID:   {top_hit.get('chunk_id')}")
    print(f"   Doc Title:  {top_hit.get('title')}")
    print(f"   Citation:   {top_hit.get('citation')}")
    print(f"   Excerpt:    {top_hit.get('content')[:120]}...")

print("\n" + "=" * 80)
print(f"AVERAGE END-TO-END RETRIEVAL LATENCY: {sum(latencies)/len(latencies):.2f} ms")
print("=" * 80)

