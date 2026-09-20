from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChoiceQuestion(BaseModel):
    type: Literal["choice"]
    instructions: str
    criteria: dict[str, str | None]

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value):
        if len(value) < 2:
            raise ValueError("Choice requires at least two criteria.")
        return value


class NoulCriteria(BaseModel):
    true: str
    false: str


class NoulQuestion(BaseModel):
    type: Literal["noul"]
    instructions: str
    criteria: NoulCriteria | None = None


class RelationQuestion(BaseModel):
    type: Literal["relation"]
    proposition: str
    contradiction: str
    threshold: float = Field(default=0.5, gt=0.0, lt=1.0)


class ScoreQuestion(BaseModel):
    type: Literal["score"]
    instructions: str
    criteria: list[str]

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value):
        if len(value) < 2:
            raise ValueError("Score requires at least two levels.")

        if len(set(value)) != len(value):
            raise ValueError("Score criteria must be unique.")

        return value


Question = Annotated[
    ChoiceQuestion | NoulQuestion | RelationQuestion | ScoreQuestion,
    Field(discriminator="type"),
]


class SystemOneRequest(BaseModel):
    state: Any

    # Optional for now.
    # This will help later when we point the official SDK at OpenDecision.
    model: str | None = None

    questions: dict[str, Question]

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, value):
        if not value:
            raise ValueError("At least one question is required.")
        return value


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, dict[str, Any]]
    usage: Usage


class DocumentDecisionRequest(BaseModel):
    document: Any
    questions: dict[str, Question]
    noul_mode: Literal["binary", "three_way", "both"] = "both"
    top_k: int = Field(default=4, ge=1, le=20)
    chunk_tokens: int = Field(default=384, ge=32, le=4096)

    @field_validator("questions")
    @classmethod
    def validate_document_questions(cls, value):
        if not value:
            raise ValueError("At least one question is required.")
        return value


class DocumentDecisionResponse(BaseModel):
    model: str
    chunks: int
    answers: dict[str, dict[str, Any]]
    usage: Usage
