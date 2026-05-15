from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.chat import Message


OFF_TOPIC_PATTERNS = [
    r"\bsalary\b",
    r"\bcompensation\b",
    r"\blegal\b",
    r"\blawyer\b",
    r"\bcontract\b",
    r"\bvisa\b",
    r"\bwork permit\b",
    r"\binterview questions?\b",
    r"\bhacking\b",
    r"\bexploit\b",
    r"\bmalware\b",
    r"\bignore (all )?(previous|above|system)\b",
    r"\bsystem prompt\b",
    r"\breveal\b.*\binstructions\b",
]

ROLE_SIGNALS = {
    "developer",
    "engineer",
    "java",
    "python",
    "javascript",
    "react",
    "sales",
    "manager",
    "graduate",
    "customer",
    "service",
    "contact",
    "finance",
    "accounting",
    "admin",
    "leadership",
    "stakeholder",
    "personality",
    "cognitive",
    "ability",
    "aptitude",
    "simulation",
    "coding",
    "sql",
}

TYPE_KEYWORDS = {
    "A": {"ability", "aptitude", "cognitive", "reasoning", "numerical", "verbal", "gsa"},
    "B": {"situational", "judgement", "biodata", "sjt"},
    "C": {"competency", "competencies", "skills", "behaviors", "behaviours", "gsa"},
    "D": {"development", "360", "feedback"},
    "E": {"exercise", "assessment center", "in basket", "role play"},
    "K": {"knowledge", "skills", "technical", "coding", "java", "python", "sql", "developer"},
    "P": {"personality", "behavior", "behaviour", "opq", "culture", "work style"},
    "S": {"simulation", "hands-on", "practical", "call center", "contact center"},
}


@dataclass(frozen=True)
class ConversationState:
    messages: list[Message]
    latest_user: str
    user_text: str
    turn_count: int
    is_refusal: bool
    is_comparison: bool
    is_vague: bool
    desired_types: set[str]


class ConversationAnalyzer:
    def analyze(self, messages: list[Message]) -> ConversationState:
        latest_user = next((message.content for message in reversed(messages) if message.role == "user"), "")
        user_messages = [message.content for message in messages if message.role == "user"]
        user_text = "\n".join(user_messages)
        is_refusal = self._is_off_topic(latest_user)
        is_comparison = self._is_comparison(latest_user)
        desired_types = self._desired_types(user_text)
        is_vague = self._is_vague(user_text, messages)
        return ConversationState(
            messages=messages,
            latest_user=latest_user,
            user_text=user_text,
            turn_count=len(messages),
            is_refusal=is_refusal,
            is_comparison=is_comparison,
            is_vague=is_vague,
            desired_types=desired_types,
        )

    def _is_off_topic(self, text: str) -> bool:
        lowered = text.lower()
        if "shl" in lowered and ("assessment" in lowered or "test" in lowered):
            return False
        return any(re.search(pattern, lowered) for pattern in OFF_TOPIC_PATTERNS)

    def _is_comparison(self, text: str) -> bool:
        lowered = text.lower()
        return bool(
            re.search(r"\b(vs\.?|versus|compare|difference between|different from)\b", lowered)
            or re.search(r"\bbetween .+ and .+\b", lowered)
        )

    def _desired_types(self, text: str) -> set[str]:
        lowered = text.lower()
        types: set[str] = set()
        for code, keywords in TYPE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                types.add(code)
        return types

    def _is_vague(self, user_text: str, messages: list[Message]) -> bool:
        lowered = user_text.lower()
        if len(messages) >= 3:
            return False
        if len(lowered.split()) >= 9:
            return False
        if any(signal in lowered for signal in ROLE_SIGNALS):
            return False
        if "assessment" in lowered or "test" in lowered or "shl" in lowered:
            return True
        return len(lowered.split()) <= 4

    def extract_comparison_names(self, text: str) -> list[str]:
        cleaned = re.sub(r"[?!.]", "", text.strip())
        patterns = [
            r"difference between (?P<a>.+?) and (?P<b>.+)$",
            r"compare (?P<a>.+?) (?:and|with|to|vs\.?|versus) (?P<b>.+)$",
            r"(?P<a>.+?)\s+(?:vs\.?|versus)\s+(?P<b>.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return [self._trim_name(match.group("a")), self._trim_name(match.group("b"))]
        return []

    def _trim_name(self, value: str) -> str:
        return re.sub(r"^(what is|what's|the|an|a)\s+", "", value.strip(), flags=re.IGNORECASE).strip()

