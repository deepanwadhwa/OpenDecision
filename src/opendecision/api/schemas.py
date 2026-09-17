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
    ChoiceQuestion | NoulQuestion | ScoreQuestion,
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