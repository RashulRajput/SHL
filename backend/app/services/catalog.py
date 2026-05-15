from __future__ import annotations

import json
import logging
import re
from functools import cached_property
from pathlib import Path

from app.models.assessment import Assessment
from app.schemas.chat import Recommendation
from app.utils.config import settings


logger = logging.getLogger(__name__)
CATALOG_URL_PATTERN = re.compile(r"^https://www\.shl\.com/products/product-catalog/view/[^\s]+/$")
ALIASES = {
    "opq": "occupational personality questionnaire opq32r",
    "opq32": "occupational personality questionnaire opq32r",
    "opq32r": "occupational personality questionnaire opq32r",
    "gsa": "global skills assessment",
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


class CatalogRepository:
    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or settings.catalog_path

    @cached_property
    def assessments(self) -> list[Assessment]:
        path = self.catalog_path if self.catalog_path.exists() else settings.seed_catalog_path
        if not path.exists():
            logger.warning("No catalog data found at %s or %s", self.catalog_path, settings.seed_catalog_path)
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("assessments", raw if isinstance(raw, list) else [])
        assessments: list[Assessment] = []
        for item in items:
            try:
                assessment = Assessment.model_validate(item)
            except Exception as exc:  # pragma: no cover - defensive data hygiene
                logger.warning("Skipping invalid assessment row: %s", exc)
                continue
            if CATALOG_URL_PATTERN.match(assessment.url) and self._is_individual_test_solution(assessment):
                assessments.append(assessment)
        logger.info("Loaded %d SHL Individual Test Solutions", len(assessments))
        return assessments

    @cached_property
    def by_url(self) -> dict[str, Assessment]:
        return {item.url: item for item in self.assessments}

    @cached_property
    def by_normalized_name(self) -> dict[str, Assessment]:
        return {normalize_name(item.name): item for item in self.assessments}

    def as_recommendation(self, assessment: Assessment) -> Recommendation:
        trusted = self.by_url.get(assessment.url)
        if trusted is None:
            raise ValueError("assessment is not from catalog")
        return Recommendation(
            name=trusted.name,
            url=trusted.url,
            test_type=trusted.test_type_display,
        )

    def safe_recommendations(self, assessments: list[Assessment], limit: int = 10) -> list[Recommendation]:
        seen: set[str] = set()
        recommendations: list[Recommendation] = []
        for assessment in assessments:
            if assessment.url in seen or assessment.url not in self.by_url:
                continue
            seen.add(assessment.url)
            recommendations.append(self.as_recommendation(assessment))
            if len(recommendations) >= limit:
                break
        return recommendations

    def _is_individual_test_solution(self, assessment: Assessment) -> bool:
        lowered = assessment.name.lower()
        packaged_markers = (" solution", "solutions", "bundle", "package")
        return not any(marker in lowered for marker in packaged_markers)

    def find_by_name(self, name: str) -> Assessment | None:
        normalized = normalize_name(name)
        if not normalized:
            return None
        normalized = ALIASES.get(normalized, normalized)
        direct = self.by_normalized_name.get(normalized)
        if direct:
            return direct

        query_tokens = set(normalized.split())
        best: tuple[float, Assessment] | None = None
        for candidate_name, assessment in self.by_normalized_name.items():
            candidate_tokens = set(candidate_name.split())
            if not candidate_tokens:
                continue
            overlap = len(query_tokens & candidate_tokens) / max(len(query_tokens), len(candidate_tokens))
            compact_match = normalized.replace(" ", "") in candidate_name.replace(" ", "")
            score = overlap + (0.4 if compact_match else 0.0)
            if best is None or score > best[0]:
                best = (score, assessment)
        return best[1] if best and best[0] >= 0.34 else None
