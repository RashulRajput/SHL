from __future__ import annotations

import re

from app.models.assessment import Assessment
from app.retrieval.ranker import HybridRetriever
from app.services.catalog import CatalogRepository
from app.services.conversation import ConversationAnalyzer, ConversationState
from app.services.gemini import GeminiClient


class RecommendationEngine:
    def __init__(
        self,
        catalog: CatalogRepository | None = None,
        retriever: HybridRetriever | None = None,
        gemini: GeminiClient | None = None,
    ) -> None:
        self.catalog = catalog or CatalogRepository()
        self.retriever = retriever or HybridRetriever(self.catalog)
        self.gemini = gemini or GeminiClient()
        self.analyzer = ConversationAnalyzer()

    def recommend(self, state: ConversationState) -> tuple[str, list[Assessment]]:
        query = self._build_query(state)
        results = self.retriever.search(query, limit=24, desired_types=state.desired_types or None)
        diversified = self._diversify([result.assessment for result in results], state)
        shortlist = diversified[:10]
        reply = self.gemini.draft_recommendation_reply(state, shortlist).text
        return reply, shortlist

    def compare(self, state: ConversationState) -> tuple[str, list[Assessment]]:
        names = self.analyzer.extract_comparison_names(state.latest_user)
        matched: list[Assessment] = []
        for name in names:
            assessment = self.catalog.find_by_name(name)
            if assessment is None:
                search_results = self.retriever.search(name, limit=1)
                assessment = search_results[0].assessment if search_results else None
            if assessment and assessment.url not in {item.url for item in matched}:
                matched.append(assessment)

        if len(matched) < 2:
            search_results = self.retriever.search(state.latest_user, limit=6)
            for result in search_results:
                if result.assessment.url not in {item.url for item in matched}:
                    matched.append(result.assessment)
                if len(matched) == 2:
                    break

        shortlist = matched[:2]
        reply = self.gemini.draft_comparison_reply(state, shortlist).text
        return reply, shortlist

    def _build_query(self, state: ConversationState) -> str:
        text = state.user_text
        latest = state.latest_user.lower()
        if "add personality" in latest or "personality" in latest:
            text += "\ninclude workplace personality behavior OPQ"
        if "stakeholder" in latest or "communication" in latest:
            text += "\ncommunication stakeholder collaboration competencies"
        if "java" in latest:
            text += "\nJava developer programming knowledge"
        if "mid" in latest or "4 years" in latest:
            text += "\nMid-Professional Professional Individual Contributor"
        return text

    def _diversify(self, assessments: list[Assessment], state: ConversationState) -> list[Assessment]:
        if not assessments:
            return []

        selected: list[Assessment] = []
        seen: set[str] = set()

        def add_assessment(assessment: Assessment | None) -> None:
            if assessment and assessment.url not in seen:
                selected.append(assessment)
                seen.add(assessment.url)

        def add_matching(predicate) -> None:
            for assessment in assessments:
                if assessment.url in seen:
                    continue
                if predicate(assessment):
                    add_assessment(assessment)
                    break

        text = state.user_text.lower()
        if re.search(r"\b(java|python|javascript|react|developer|engineer|technical|coding)\b", text):
            add_matching(lambda item: "K" in item.test_types)
        if re.search(r"\b(personality|behavior|behaviour|culture|work style|opq)\b", text):
            add_assessment(self.catalog.find_by_name("Occupational Personality Questionnaire OPQ32r"))
            add_matching(lambda item: "P" in item.test_types)
        if re.search(r"\b(stakeholders?|leadership|managers?|communication|collaboration)\b", text):
            add_assessment(self.catalog.find_by_name("Global Skills Assessment"))
            add_assessment(self.catalog.find_by_name("Occupational Personality Questionnaire OPQ32r"))
            add_matching(lambda item: "P" in item.test_types)
        if re.search(r"\b(cognitive|aptitude|ability|reasoning|graduate|entry)\b", text):
            add_matching(lambda item: "A" in item.test_types)
            if not any("A" in item.test_types for item in selected):
                add_assessment(self.catalog.find_by_name("Verify - General Ability Screen"))
        if re.search(r"\b(simulation|practical|hands|contact center|customer service)\b", text):
            add_matching(lambda item: "S" in item.test_types)

        for assessment in assessments:
            if assessment.url not in seen:
                selected.append(assessment)
                seen.add(assessment.url)
            if len(selected) >= 10:
                break
        return selected
