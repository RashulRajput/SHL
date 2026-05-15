from __future__ import annotations

import re
from collections import Counter


TOKEN_PATTERN = re.compile(r"[a-z0-9+#.]+")
STOPWORDS = {
    "a",
    "about",
    "actually",
    "add",
    "also",
    "an",
    "and",
    "any",
    "around",
    "assessment",
    "assessments",
    "candidate",
    "candidates",
    "for",
    "give",
    "hiring",
    "i",
    "in",
    "is",
    "me",
    "need",
    "of",
    "or",
    "please",
    "recommend",
    "recruiting",
    "role",
    "test",
    "tests",
    "the",
    "to",
    "we",
    "with",
}

SYNONYMS = {
    "developer": ["programmer", "software", "coding", "technical"],
    "engineer": ["software", "technical", "coding"],
    "java": ["j2ee", "spring", "backend"],
    "javascript": ["js", "node", "react", "front end", "frontend"],
    "frontend": ["react", "javascript", "html", "css"],
    "backend": ["api", "server", "database", "java", "python"],
    "manager": ["leadership", "supervisor", "management"],
    "sales": ["account", "customer", "negotiation"],
    "personality": ["behavior", "behaviour", "opq", "workplace"],
    "cognitive": ["ability", "aptitude", "reasoning", "general ability"],
    "communication": ["verbal", "stakeholder", "english"],
    "finance": ["accounting", "payable", "receivable", "bank"],
    "graduate": ["entry", "early", "campus"],
}


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS]


def expanded_tokens(text: str) -> list[str]:
    tokens = tokenize(text)
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, []))
    return tokenize(" ".join(expanded))


def term_counter(text: str) -> Counter[str]:
    return Counter(expanded_tokens(text))

