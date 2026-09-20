import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from opendecision import __version__
from opendecision.api.schemas import (
    ChoiceQuestion,
    DocumentDecisionRequest,
    DocumentDecisionResponse,
    NoulQuestion,
    RelationQuestion,
    ScoreQuestion,
    SystemOneRequest,
    SystemOneResponse,
    Usage,
)
from opendecision.engine import (
    DEFAULT_MODEL,
    OpenDecisionEngine,
)
from opendecision.documents import DocumentDecisionService


API_MODEL_NAME = "modernbert-large-zeroshot-v2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting OpenDecision...")

    # Load once when the server starts.
    model = os.environ.get("OPENDECISION_MODEL", DEFAULT_MODEL)
    app.state.engine = OpenDecisionEngine(
        model=model,
    )
    app.state.model_name = model

    print("OpenDecision ready.")

    yield

    print("Stopping OpenDecision...")


app = FastAPI(
    title="OpenDecision",
    description="Open-source semantic decision engine.",
    version=__version__,
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

        elif isinstance(question, RelationQuestion):

            result = engine.relation(
                state=payload.state,
                proposition=question.proposition,
                contradiction=question.contradiction,
                threshold=question.threshold,
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
        model=getattr(request.app.state, "model_name", API_MODEL_NAME),
        answers=answers,
        usage=Usage(
            input_tokens=estimate_input_tokens(engine, payload),
            output_tokens=0,
        ),
    )


@app.post(
    "/v1/documents/decide",
    response_model=DocumentDecisionResponse,
)
def decide_document(
    payload: DocumentDecisionRequest,
    request: Request,
):
    engine: OpenDecisionEngine = request.app.state.engine
    service = DocumentDecisionService(
        engine,
        top_k=payload.top_k,
        chunk_tokens=payload.chunk_tokens,
    )
    try:
        chunks = service.chunks(payload.document)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    answers = {}

    for question_name, question in payload.questions.items():
        if isinstance(question, ChoiceQuestion):
            result = service.choice(
                chunks=chunks,
                instructions=question.instructions,
                criteria=question.criteria,
            )
        elif isinstance(question, NoulQuestion):
            criteria = (
                question.criteria.model_dump()
                if question.criteria is not None
                else None
            )
            result = service.noul(
                chunks=chunks,
                instructions=question.instructions,
                criteria=criteria,
                mode=payload.noul_mode,
            )
        elif isinstance(question, RelationQuestion):
            result = service.relation(
                chunks=chunks,
                proposition=question.proposition,
                contradiction=question.contradiction,
                threshold=question.threshold,
            )
        elif isinstance(question, ScoreQuestion):
            result = service.score(
                chunks=chunks,
                instructions=question.instructions,
                criteria=question.criteria,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported question type for {question_name}",
            )

        answers[question_name] = result

    token_payload = SystemOneRequest(
        state=payload.document,
        questions=payload.questions,
    )
    return DocumentDecisionResponse(
        model=getattr(request.app.state, "model_name", API_MODEL_NAME),
        chunks=len(chunks),
        answers=answers,
        usage=Usage(
            input_tokens=estimate_input_tokens(engine, token_payload),
            output_tokens=0,
        ),
    )
