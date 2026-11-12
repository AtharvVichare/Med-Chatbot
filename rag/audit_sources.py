import json
from pathlib import Path
import pymupdf

docs_info = [
    {
        'id': 'WHO-HTN-GUIDELINE-2021',
        'file': 'data/reference/guidelines/who_hypertension_guideline_2021.pdf',
        'type': 'PDF',
        'org': 'World Health Organization (WHO)',
        'scope': 'Pharmacological Treatment of Hypertension in Adults',
        'completeness': 'Curated Technical Recommendations Excerpt (2 pages, core thresholds & medication classes)'
    },
    {
        'id': 'WHO-HEARTS-CVD-2020',
        'file': 'data/reference/guidelines/who_hearts_cvd_package.pdf',
        'type': 'PDF',
        'org': 'World Health Organization (WHO)',
        'scope': 'HEARTS Technical Package for CVD in Primary Care',
        'completeness': 'Curated Core Modules Excerpt (1 page, lifestyle counseling & protocolized medications)'
    },
    {
        'id': 'MEDLINEPLUS-DIABETES-XML',
        'file': 'data/reference/xml/medlineplus_diabetes.xml',
        'type': 'XML',
        'org': 'U.S. NLM / NIH',
        'scope': 'MedlinePlus Topic: Diabetes Mellitus',
        'completeness': 'Complete Topic Summary & Diagnostic/Treatment Sections'
    },
    {
        'id': 'MEDLINEPLUS-HYPERTENSION-XML',
        'file': 'data/reference/xml/medlineplus_hypertension.xml',
        'type': 'XML',
        'org': 'U.S. NLM / NIH',
        'scope': 'MedlinePlus Topic: High Blood Pressure',
        'completeness': 'Complete Topic Summary & Category/Threshold Sections'
    }
]

print(f"{'Document ID':<28} | {'Type':<5} | {'Pages/Sections':<15} | {'Chunks':<7} | {'Tokens':<8} | {'Completeness'}")
print("-" * 115)

total_chunks = 0
total_tokens = 0

for d in docs_info:
    p = Path(d['file'])
    if d['type'] == 'PDF':
        doc = pymupdf.open(str(p))
        pages_str = f"{len(doc)} pages"
        doc.close()
    else:
        pages_str = "Full XML Record"
        
    jsonl_path = Path('data/processed') / f"{d['id']}.jsonl"
    chunks = [json.loads(line) for line in open(jsonl_path, encoding='utf-8')] if jsonl_path.exists() else []
    tokens = sum(c.get('token_count', 0) for c in chunks)
    total_chunks += len(chunks)
    total_tokens += tokens
    print(f"{d['id']:<28} | {d['type']:<5} | {pages_str:<15} | {len(chunks):<7} | {tokens:<8} | {d['completeness']}")

print("-" * 115)
print(f"{'Total Ingested':<28} | {'':<5} | {'':<15} | {total_chunks:<7} | {total_tokens:<8} | 4 authoritative sources audited")

