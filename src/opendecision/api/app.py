import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from opendecision.api.schemas import (
    ChoiceQuestion,
    NoulQuestion,
    ScoreQuestion,
    SystemOneRequest,
    SystemOneResponse,
    Usage,
)
from opendecision.engine import (
    DEFAULT_MODEL,
    OpenDecisionEngine,
)


API_MODEL_NAME = "modernbert-large-zeroshot-v2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting OpenDecision...")

    # Load once when the server starts.
    app.state.engine = OpenDecisionEngine(
        model=DEFAULT_MODEL,
    )

    print("OpenDecision ready.")

    yield

    print("Stopping OpenDecision...")


app = FastAPI(
    title="OpenDecision",
    description="Open-source semantic decision engine.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "OpenDecision",
    }


def estimate_input_tokens(
    engine: OpenDecisionEngine,
    payload: SystemOneRequest,
) -> int:
    """
    Approximate logical API input size.

    This is NOT currently intended to represent actual transformer
    compute, because zero-shot classification may evaluate the same
    state against multiple candidate hypotheses.
    """

    serialized = json.dumps(
        payload.model_dump(),
        ensure_ascii=False,
        sort_keys=True,
    )

    tokens = engine.classifier.tokenizer(
        serialized,
        add_special_tokens=False,
    )

    return len(tokens["input_ids"])


@app.post(
    "/v1/systemone",
    response_model=SystemOneResponse,
)
def system_one(
    payload: SystemOneRequest,
    request: Request,
):
    engine: OpenDecisionEngine = request.app.state.engine

    answers = {}

    for question_name, question in payload.questions.items():

        if isinstance(question, ChoiceQuestion):

            result = engine.choice(
                state=payload.state,
                instructions=question.instructions,
                criteria=question.criteria,
            )

        elif isinstance(question, NoulQuestion):

            criteria = None

            if question.criteria is not None:
                criteria = question.criteria.model_dump()

            result = engine.noul(
                state=payload.state,
                instructions=question.instructions,
                criteria=criteria,
            )

        elif isinstance(question, ScoreQuestion):

            result = engine.score(
                state=payload.state,
                instructions=question.instructions,
                criteria=question.criteria,
            )

        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported question type for {question_name}",
            )

        answers[question_name] = result

    return SystemOneResponse(
        model=API_MODEL_NAME,
        answers=answers,
        usage=Usage(
            input_tokens=estimate_input_tokens(engine, payload),
            output_tokens=0,
        ),
    )