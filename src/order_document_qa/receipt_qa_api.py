from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .order_qa_service import OrderQuestionService, QuestionAnswer, QuestionRequest

app = FastAPI(title="Order document QA", version="0.1.0")


def build_service() -> OrderQuestionService:
    return OrderQuestionService(
        client=InfraiClient(),
        collection=os.getenv("INFRAI_COLLECTION", "commerce-order-documents"),
        embedding_model=os.getenv("INFRAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )


@app.post("/questions", response_model=QuestionAnswer)
def ask_order_question(request: QuestionRequest) -> QuestionAnswer:
    try:
        return build_service().answer(request)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code, "error": exc.detail}) from exc


def run() -> None:
    uvicorn.run("order_document_qa.receipt_qa_api:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()

