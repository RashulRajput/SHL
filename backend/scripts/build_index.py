from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.catalog import CatalogRepository
from app.utils.config import settings


def build_index(chroma_path: Path, reset: bool = True) -> None:
    catalog = CatalogRepository()
    assessments = catalog.assessments
    if not assessments:
        raise RuntimeError("No catalog rows available. Run scripts/scrape_catalog.py first.")

    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    if reset:
        try:
            client.delete_collection(settings.collection_name)
        except Exception:
            pass
    collection = client.get_or_create_collection(settings.collection_name)
    embedder = SentenceTransformer(settings.embedding_model)
    documents = [assessment.retrieval_text for assessment in assessments]
    vectors = embedder.encode(documents, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    collection.upsert(
        ids=[assessment.url for assessment in assessments],
        embeddings=[vector.tolist() for vector in vectors],
        documents=documents,
        metadatas=[
            {
                "name": assessment.name,
                "url": assessment.url,
                "test_type": assessment.test_type_display,
                "duration": assessment.duration,
            }
            for assessment in assessments
        ],
    )
    print(f"Indexed {collection.count()} assessments in {chroma_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local Chroma index for SHL assessments.")
    parser.add_argument("--chroma-path", type=Path, default=settings.chroma_path)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args()
    build_index(args.chroma_path, reset=not args.no_reset)


if __name__ == "__main__":
    main()
