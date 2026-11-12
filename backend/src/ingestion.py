from enum import _EnumerationT
from langchain_core import documents
import re
import sys
from pathlib import Path
from typing import List

from langchain.schema import  Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CHUNK_SIZE, CHUNK_OVERLAP
from src.logger import get_logger

log = get_logger(__name__)

def clean_text(text:str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = text.replace("\u2013", "-").replace("\u2014", "--")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def load_document(pdf_path:str) -> List[Document]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not Found:{path}")

    log.info(f"Loading PDF:{path.name}")
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    log.info(f"Total Pages: {total_pages}")

    documents = []
    for page_num, page in enumerate(reader.pages, start = 1):
        raw = page.extract_text() or ""
        clean = clean_text(raw)
        if len(clean) < 50:
            continue
        documents.append(Document(
            page_content=clean,
            metadata={
                "source": path.name,
                "page": page_num,
                "total_pages":total_pages
            }
        ))

    log.info(f"Loaded {len(documents)} pages with content")
    return documents

def chunk_document(documents:List[Document]) -> List[Document]:
    splitter =  RecursiveCharacterTextSplitter(
        chunk_size = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators = ["\n\n", "\n", " ", ""],
        length_functions = len
    )

    log,info(f"Chunking {len(Document)} pages [size={CHUNK_SIZE}]")