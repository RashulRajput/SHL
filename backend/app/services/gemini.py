from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.models.assessment import Assessment
from app.services.conversation import ConversationState
from app.utils.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReplyDraft:
    text: str
    used_llm: bool


class GeminiClient:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key

    def available(self) -> bool:
        return bool(settings.enable_gemini and self.api_key)

    def draft_recommendation_reply(
        self,
        state: ConversationState,
        assessments: list[Assessment],
    ) -> ReplyDraft:
        fallback = self._fallback_recommendation_reply(state, assessments)
        if not self.available():
            return ReplyDraft(fallback, used_llm=False)
        context = self._format_context(assessments)
        prompt = (
            "You are an SHL assessment recommender for recruiters. "
            "Use only the catalog context below. Do not invent assessment names, URLs, durations, or claims. "
            "Write one concise paragraph, then one short sentence inviting refinement. "
            "Do not output JSON.\n\n"
            f"Conversation:\n{self._format_messages(state)}\n\n"
            f"Catalog context:\n{context}\n\n"
            "Reply:"
        )
        return self._generate(prompt, fallback=fallback, pro=False)

    def draft_comparison_reply(self, state: ConversationState, assessments: list[Assessment]) -> ReplyDraft:
        fallback = self._fallback_comparison_reply(assessments)
        if not self.available():
            return ReplyDraft(fallback, used_llm=False)
        context = self._format_context(assessments)
        prompt = (
            "Compare these SHL assessments using only the catalog context. "
            "Mention what each measures, test type, length if provided, and best-fit use. "
            "If a field is missing, say the catalog does not state it. Keep it under 160 words. "
            "Do not output JSON.\n\n"
            f"User request: {state.latest_user}\n\nCatalog context:\n{context}\n\nComparison:"
        )
        return self._generate(prompt, fallback=fallback, pro=True)

    def _generate(self, prompt: str, fallback: str, pro: bool) -> ReplyDraft:
        model = settings.gemini_pro_model if pro else settings.gemini_flash_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 220,
            },
        }
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                    timeout=settings.gemini_timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return ReplyDraft(text=self._sanitize(text), used_llm=True)
            except Exception as exc:
                logger.warning("Gemini request failed on attempt %d: %s", attempt + 1, exc)
                time.sleep(0.25 * (attempt + 1))
        return ReplyDraft(text=fallback, used_llm=False)

    def _format_messages(self, state: ConversationState) -> str:
        recent = state.messages[-6:]
        return "\n".join(f"{message.role}: {message.content}" for message in recent)

    def _format_context(self, assessments: list[Assessment]) -> str:
        lines: list[str] = []
        for idx, item in enumerate(assessments[:10], start=1):
            lines.append(
                (
                    f"{idx}. {item.name} | URL: {item.url} | Types: {item.test_type_display} | "
                    f"Length: {item.duration or 'not stated'} | Levels: {', '.join(item.job_levels[:5]) or 'not stated'} | "
                    f"Description: {item.description[:420]}"
                )
            )
        return "\n".join(lines)

    def _sanitize(self, text: str) -> str:
        return text.replace("```", "").strip()

    def _fallback_recommendation_reply(self, state: ConversationState, assessments: list[Assessment]) -> str:
        count = len(assessments)
        role_hint = " based on the role details you shared" if len(state.user_text.split()) > 5 else ""
        names = ", ".join(item.name for item in assessments[:3])
        return (
            f"I found {count} SHL Individual Test Solutions{role_hint}. "
            f"The strongest starting points are {names}. You can refine by seniority, skill area, language, or whether you want personality, aptitude, knowledge, or simulation coverage."
        )

    def _fallback_comparison_reply(self, assessments: list[Assessment]) -> str:
        if len(assessments) < 2:
            return "I can compare SHL assessments when both names are present in the catalog. Please provide the two assessment names."
        first, second = assessments[:2]
        first_description = self._shorten(first.description or "catalog-described capabilities", 260)
        second_description = self._shorten(second.description or "catalog-described capabilities", 260)
        return (
            f"{first.name} is cataloged as {first.test_type_display} and measures {first_description} "
            f"with length {first.duration or 'not stated'}. {second.name} is cataloged as {second.test_type_display} and measures "
            f"{second_description} with length {second.duration or 'not stated'}. "
            "Use the first when its measured area matches the role requirement; use the second when its catalog description is the closer hiring signal."
        )

    def _shorten(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "..."
