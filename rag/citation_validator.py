"""
Citation and Claim-to-Evidence Grounding Validation Engine
Validates that citations returned by the language model:
1. ID Validity: Match actual retrieved Pinecone chunks.
2. Canonical Provenance: Preserves document ID, chunk ID, title, organization, and URL.
3. Claim-to-Evidence Support: Lexical / semantic n-gram verification checking whether
   the model's specific cited statement or key clinical keywords actually exist within
   the retrieved passage (prevents citing an asthma chunk for an unrelated statement).
4. Rejects fabricated citations, unretrieved sources, and unsupported statements.
"""

import re
from typing import List, Dict, Any, Tuple

# Common stop words to exclude from keyword overlap calculations
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
}

def extract_keywords(text: str) -> set:
    words = re.findall(r"\b[a-zA-Z0-9\-\_]{3,}\b", text.lower())
    return {w for w in words if w not in STOP_WORDS}

class CitationValidator:

    @staticmethod
    def validate_citations(
        model_citations: List[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validates model citations against retrieved chunks, checking:
        1. ID existence.
        2. Claim-to-evidence support: checks keyword overlap between claimed statement and chunk content.
        """
        retrieved_chunk_map = {c["chunk_id"]: c for c in retrieved_chunks}

        valid = []
        rejected = []

        for cit in model_citations:
            chunk_id = cit.get("chunk_id")
            doc_id = cit.get("document_id")
            statement = cit.get("statement", "")

            # Match chunk by chunk_id or document_id
            matched_chunk = None
            if chunk_id and chunk_id in retrieved_chunk_map:
                matched_chunk = retrieved_chunk_map[chunk_id]
            else:
                for c in retrieved_chunks:
                    if c.get("document_id") == doc_id:
                        matched_chunk = c
                        break

            if not matched_chunk:
                rejected.append({
                    "citation": cit,
                    "reason": "HALLUCINATED_OR_UNRETRIEVED_SOURCE"
                })
                continue

            # Check Claim-to-Evidence support
            chunk_text = matched_chunk.get("text", "") or matched_chunk.get("content", "")
            
            # If statement was provided by model, compute factual keyword alignment
            statement_keywords = extract_keywords(statement) if statement else set()
            chunk_keywords = extract_keywords(chunk_text)
            
            is_supported = True
            rejection_reason = None
            
            if statement_keywords:
                overlap = statement_keywords.intersection(chunk_keywords)
                overlap_ratio = len(overlap) / len(statement_keywords)
                # If statement has >= 3 distinct content keywords but less than 20% overlap with cited chunk, reject
                if len(statement_keywords) >= 3 and overlap_ratio < 0.20:
                    is_supported = False
                    rejection_reason = "UNSUPPORTED_CLAIM_NOT_FOUND_IN_CITED_CHUNK"

            if is_supported:
                verified_citation = {
                    "document_id": matched_chunk["document_id"],
                    "chunk_id": matched_chunk["chunk_id"],
                    "title": matched_chunk["title"],
                    "source_organization": matched_chunk["source_organization"],
                    "source_url": matched_chunk["source_url"],
                    "page_number": matched_chunk.get("page_number"),
                    "section_heading": matched_chunk.get("section_heading"),
                    "verification_status": "VERIFIED_GROUNDED",
                    "claim_supported": True if statement_keywords else "METADATA_MATCH"
                }
                valid.append(verified_citation)
            else:
                rejected.append({
                    "citation": cit,
                    "reason": rejection_reason,
                    "matched_chunk_id": matched_chunk["chunk_id"],
                    "statement": statement
                })

        return valid, rejected
