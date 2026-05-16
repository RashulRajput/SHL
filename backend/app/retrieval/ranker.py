from __future__ import annotations

import logging
import math
from collections import Counter
from dataclasses import dataclass

from app.models.assessment import Assessment
from app.retrieval.text import term_counter, tokenize
from app.services.catalog import CatalogRepository
from app.utils.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalResult:
    assessment: Assessment
    score: float
    reason: str


class HybridRetriever:
    def __init__(self, catalog: CatalogRepository | None = None) -> None:
        self.catalog = catalog or CatalogRepository()
        self._docs = self.catalog.assessments
        self._doc_counters = [term_counter(item.retrieval_text) for item in self._docs]
        self._idf = self._build_idf(self._doc_counters)
        self._chroma_collection = self._try_load_chroma()
        self._embedder = None

    def search(
        self,
        query: str,
        limit: int = 12,
        desired_types: set[str] | None = None,
    ) -> list[RetrievalResult]:
        lexical = self._lexical_search(query, limit=max(limit * 3, 20), desired_types=desired_types)
        semantic = self._semantic_search(query, limit=max(limit * 2, 12), desired_types=desired_types)
        merged: dict[str, RetrievalResult] = {result.assessment.url: result for result in lexical}
        for result in semantic:
            existing = merged.get(result.assessment.url)
            if existing:
                merged[result.assessment.url] = RetrievalResult(
                    assessment=result.assessment,
                    score=existing.score + result.score * 0.35,
                    reason=f"{existing.reason}; semantic match",
                )
            else:
                merged[result.assessment.url] = result
        ranked = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    def _build_idf(self, counters: list[Counter[str]]) -> dict[str, float]:
        doc_count = max(len(counters), 1)
        document_frequency: Counter[str] = Counter()
        for counter in counters:
            document_frequency.update(counter.keys())
        return {
            term: math.log((1 + doc_count) / (1 + frequency)) + 1
            for term, frequency in document_frequency.items()
        }

    def _lexical_search(
        self,
        query: str,
        limit: int,
        desired_types: set[str] | None,
    ) -> list[RetrievalResult]:
        query_counter = term_counter(query)
        if not query_counter:
            return []

        results: list[RetrievalResult] = []
        for assessment, doc_counter in zip(self._docs, self._doc_counters):
            if desired_types and not desired_types.intersection(assessment.test_types):
                type_overlap = 0
            else:
                type_overlap = 1

            score = 0.0
            matched_terms: list[str] = []
            for term, query_weight in query_counter.items():
                if term in doc_counter:
                    score += query_weight * (1 + math.log(1 + doc_counter[term])) * self._idf.get(term, 1)
                    matched_terms.append(term)

            score += self._domain_boost(query, assessment)
            if desired_types and type_overlap:
                score += 2.5
            if score > 0:
                reason = "matched " + ", ".join(matched_terms[:5]) if matched_terms else "domain signal"
                results.append(RetrievalResult(assessment=assessment, score=score, reason=reason))

        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]

    def _domain_boost(self, query: str, assessment: Assessment) -> float:
        q_tokens = set(tokenize(query))
        name = assessment.name.lower()
        text = assessment.retrieval_text.lower()
        boost = 0.0

        # Generic tech knowledge boost — applies equally to all tech stacks
        tech_terms = {"java", "python", "javascript", "react", "sql", "developer", "engineer", "coding",
                      "c#", ".net", "ruby", "php", "swift", "kotlin", "typescript", "go", "rust"}
        if q_tokens & tech_terms and "K" in assessment.test_types:
            boost += 1.5

        # Generic name match — any query token appearing in assessment name
        for token in q_tokens:
            if len(token) > 2 and token in name:
                boost += 2.0

        # Stakeholder / communication / leadership
        if q_tokens & {"stakeholder", "communication", "manager", "leadership"} and (
            {"P", "C", "B"} & set(assessment.test_types)
        ):
            boost += 1.4

        # Personality / behavioral assessments
        if q_tokens & {"personality", "behavior", "behaviour", "culture"} and "P" in assessment.test_types:
            boost += 2.2

        # Cognitive / aptitude assessments
        if q_tokens & {"cognitive", "aptitude", "ability", "reasoning"} and "A" in assessment.test_types:
            boost += 2.0

        # Simulation / practical assessments
        if q_tokens & {"simulation", "hands", "practical"} and "S" in assessment.test_types:
            boost += 2.0

        # Graduate / entry-level
        if q_tokens & {"graduate", "entry", "campus"} and (
            "graduate" in text or "entry" in text or "general population" in text
        ):
            boost += 1.4

        # Marketing / sales / customer roles
        if q_tokens & {"marketing", "sales", "customer", "account", "negotiation", "advertising"}:
            if any(kw in text for kw in ["sales", "customer", "marketing", "account", "negotiation"]):
                boost += 2.5

        # Finance / accounting roles
        if q_tokens & {"finance", "accounting", "bank", "payable", "receivable", "financial"}:
            if any(kw in text for kw in ["finance", "accounting", "bank", "payable", "receivable"]):
                boost += 2.5

        # HR / people management
        if q_tokens & {"hr", "human", "resources", "people", "talent"}:
            if any(kw in text for kw in ["hr", "human resource", "people", "talent"]):
                boost += 2.0

        # Data / analytics roles
        if q_tokens & {"data", "analytics", "analyst", "science", "statistics"}:
            if any(kw in text for kw in ["data", "analytics", "analyst", "numerical"]):
                boost += 2.0

        # Named assessment aliases (OPQ, GSA)
        if q_tokens & {"opq"} and "opq" in name:
            boost += 5.0
        if q_tokens & {"gsa"} and "global skills assessment" in name:
            boost += 5.0

        return boost

    def _try_load_chroma(self):
        try:
            import chromadb  # type: ignore

            if not settings.chroma_path.exists():
                return None
            client = chromadb.PersistentClient(path=str(settings.chroma_path))
            collection = client.get_collection(settings.collection_name)
            if collection.count() == 0:
                return None
            logger.info("Loaded Chroma collection %s", settings.collection_name)
            return collection
        except Exception as exc:
            logger.info("Chroma unavailable, using deterministic lexical retrieval: %s", exc)
            return None

    def _semantic_search(
        self,
        query: str,
        limit: int,
        desired_types: set[str] | None,
    ) -> list[RetrievalResult]:
        if self._chroma_collection is None:
            return []
        try:
            embedder = self._get_embedder()
            vector = embedder.encode([query], normalize_embeddings=True)[0].tolist()
            response = self._chroma_collection.query(
                query_embeddings=[vector],
                n_results=min(limit, len(self._docs)),
                include=["metadatas", "distances"],
            )
        except Exception as exc:
            logger.warning("Semantic retrieval failed, continuing with lexical results: %s", exc)
            return []

        urls = response.get("ids", [[]])[0]
        distances = response.get("distances", [[]])[0]
        results: list[RetrievalResult] = []
        for url, distance in zip(urls, distances):
            assessment = self.catalog.by_url.get(url)
            if assessment is None:
                continue
            if desired_types and not desired_types.intersection(assessment.test_types):
                continue
            score = max(0.0, 2.0 - float(distance))
            results.append(RetrievalResult(assessment=assessment, score=score, reason="semantic match"))
        return results

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._embedder = SentenceTransformer(settings.embedding_model)
        return self._embedder
