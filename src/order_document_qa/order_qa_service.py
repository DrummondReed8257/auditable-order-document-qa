from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class QuestionRequest:
    team_id: str
    order_id: str
    question: str

    def __post_init__(self) -> None:
        if not self.team_id:
            raise ValueError("team_id must not be empty")
        if not self.order_id:
            raise ValueError("order_id must not be empty")
        if not 3 <= len(self.question) <= 500:
            raise ValueError("question must contain between 3 and 500 characters")


@dataclass(frozen=True)
class Evidence:
    document_id: str
    document_type: str
    excerpt: str


@dataclass(frozen=True)
class QuestionAnswer:
    order_id: str
    answer: str
    evidence: list[Evidence]


@dataclass(frozen=True)
class OrderQuestionService:
    client: InfraiClient
    collection: str
    embedding_model: str

    def answer(self, request: QuestionRequest) -> QuestionAnswer:
        embedding = self.client.embed(request.question, self.embedding_model)
        query_data = self.client.query(
            self.collection,
            embedding,
            request.team_id,
            request.order_id,
            top_k=8,
        )
        matches = query_data.get("matches", query_data.get("vectors", []))
        owned = [item for item in matches if self._belongs_to_request(item, request)]
        if not owned:
            return QuestionAnswer(
                order_id=request.order_id,
                answer="No matching order evidence was found.",
                evidence=[],
            )

        candidates = [str(item["metadata"]["text"]) for item in owned]
        ranked_data = self.client.rerank(request.question, candidates, top_k=min(3, len(candidates)))
        ranked = ranked_data.get("results", ranked_data.get("items", []))
        selected = self._select_ranked(owned, candidates, ranked)
        evidence = [
            Evidence(
                document_id=str(item["metadata"]["document_id"]),
                document_type=str(item["metadata"]["document_type"]),
                excerpt=str(item["metadata"]["text"]),
            )
            for item in selected
        ]
        summary = " ".join(item.excerpt for item in evidence)
        return QuestionAnswer(order_id=request.order_id, answer=summary, evidence=evidence)

    @staticmethod
    def _belongs_to_request(item: dict[str, Any], request: QuestionRequest) -> bool:
        metadata = item.get("metadata") or {}
        return metadata.get("team_id") == request.team_id and metadata.get("order_id") == request.order_id

    @staticmethod
    def _select_ranked(
        owned: list[dict[str, Any]],
        candidates: list[str],
        ranked: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_text = {str(item["metadata"]["text"]): item for item in owned}
        selected: list[dict[str, Any]] = []
        for result in ranked:
            index = result.get("index")
            text = result.get("text") or result.get("candidate")
            if isinstance(index, int) and 0 <= index < len(candidates):
                text = candidates[index]
            if text in by_text and by_text[text] not in selected:
                selected.append(by_text[text])
        return selected or owned[:3]
