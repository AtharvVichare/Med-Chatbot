"""
Dataset Downloader & Provenance Recorder for SymbiPredict (SDPD)
Downloads symbipredict_2022.csv from official Mendeley Data public repository.
Preserves:
- Raw file unchanged at data/disease_prediction/raw/symbipredict_2022.csv
- Source metadata, DOI, license, and download timestamp at data/disease_prediction/raw/dataset_manifest.json
- Validates SHA-256 against Mendeley reported hash
"""

import os
import json
import hashlib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATASET_DIR = Path("data/disease_prediction/raw")
DATASET_DIR.mkdir(parents=True, exist_ok=True)

CSV_TARGET_PATH = DATASET_DIR / "symbipredict_2022.csv"
MANIFEST_TARGET_PATH = DATASET_DIR / "dataset_manifest.json"

DOWNLOAD_URL = "https://data.mendeley.com/public-files/datasets/dv5z3v2xyd/files/72d80d7b-a027-480c-99a7-c3dd3815bdf1/file_downloaded"
EXPECTED_SHA256 = "9834c90dd48eb2fef1fa56282f8f016a6781b0e4ada878015dc34a81af8e9e1b"
EXPECTED_SIZE = 1382907

def download_and_verify():
    print(f"Downloading {CSV_TARGET_PATH.name} from official Mendeley URL...")
    req = urllib.request.Request(DOWNLOAD_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*"
    })
    
    with urllib.request.urlopen(req) as resp, open(CSV_TARGET_PATH, "wb") as out_f:
        bytes_copied = 0
        while chunk := resp.read(65536):
            out_f.write(chunk)
            bytes_copied += len(chunk)
            
    print(f"Downloaded {bytes_copied} bytes.")
    
    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(CSV_TARGET_PATH, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_sha256 = hasher.hexdigest()
    actual_size = CSV_TARGET_PATH.stat().st_size
    
    print(f"Actual SHA-256:   {actual_sha256}")
    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    assert actual_sha256 == EXPECTED_SHA256, f"Checksum mismatch! {actual_sha256} != {EXPECTED_SHA256}"
    assert actual_size == EXPECTED_SIZE, f"Size mismatch! {actual_size} != {EXPECTED_SIZE}"
    print("[SUCCESS] SHA-256 and byte size perfectly match Mendeley official record.")

    manifest = {
        "dataset_name": "SymbiPredict - Symptom-Disease Prediction Dataset (SDPD)",
        "publisher": "Mendeley Data",
        "doi": "10.17632/dv5z3v2xyd.1",
        "dataset_url": "https://data.mendeley.com/datasets/dv5z3v2xyd/1",
        "download_url": DOWNLOAD_URL,
        "author": "Jay Tucker",
        "institution": "CDC Development Solutions",
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "license_url": "http://creativecommons.org/licenses/by/4.0",
        "publish_date": "2024-04-02T15:42:51.172Z",
        "download_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "filename": "symbipredict_2022.csv",
        "file_size_bytes": actual_size,
        "sha256": actual_sha256,
        "verification_status": "VERIFIED_OFFICIAL_HASH_MATCH",
        "provenance_note": (
            "Candidate research dataset downloaded directly from official Mendeley Data repository. "
            "Undergoes independent clinical and leakage audit for research prototyping. "
            "Not clinically validated patient data."
        )
    }
    
    with open(MANIFEST_TARGET_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved dataset metadata manifest to {MANIFEST_TARGET_PATH}")
    return manifest

if __name__ == "__main__":
    download_and_verify()

