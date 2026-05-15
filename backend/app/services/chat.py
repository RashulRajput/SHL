from __future__ import annotations

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.catalog import CatalogRepository
from app.services.conversation import ConversationAnalyzer
from app.services.recommendation import RecommendationEngine


class ChatService:
    def __init__(self) -> None:
        self.catalog = CatalogRepository()
        self.analyzer = ConversationAnalyzer()
        self.engine = RecommendationEngine(self.catalog)

    def handle(self, payload: ChatRequest) -> ChatResponse:
        state = self.analyzer.analyze(payload.messages)

        if state.is_refusal:
            return ChatResponse(
                reply=(
                    "I can only help with selecting and comparing SHL Individual Test Solutions from the SHL catalog. "
                    "Share the role, skills, seniority, or assessment constraints and I'll recommend catalog-backed options."
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        if state.is_vague:
            return ChatResponse(
                reply=(
                    "What role are you hiring for, and what do you most need to measure: technical skills, cognitive ability, "
                    "personality/work style, simulations, or job-specific competencies?"
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        if state.is_comparison:
            reply, compared = self.engine.compare(state)
            return ChatResponse(
                reply=reply,
                recommendations=self.catalog.safe_recommendations(compared, limit=10),
                end_of_conversation=False,
            )

        reply, shortlist = self.engine.recommend(state)
        return ChatResponse(
            reply=reply,
            recommendations=self.catalog.safe_recommendations(shortlist, limit=10),
            end_of_conversation=False,
        )
