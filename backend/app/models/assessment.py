from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


TEST_TYPE_LABELS: dict[str, str] = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    url: str
    description: str = ""
    test_types: list[str] = Field(default_factory=list)
    remote_testing: bool = False
    adaptive_irt: bool = False
    duration: str = ""
    job_levels: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    downloads: list[str] = Field(default_factory=list)
    source: str = "shl_catalog"

    @property
    def test_type_display(self) -> str:
        return " ".join(self.test_types) if self.test_types else "Unspecified"

    @property
    def retrieval_text(self) -> str:
        labels = [TEST_TYPE_LABELS.get(code, code) for code in self.test_types]
        parts = [
            self.name,
            self.description,
            " ".join(labels),
            " ".join(self.job_levels),
            " ".join(self.languages[:8]),
            self.duration,
        ]
        return " ".join(part for part in parts if part)

