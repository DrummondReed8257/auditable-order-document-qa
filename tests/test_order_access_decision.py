from typing import Any, cast

from order_document_qa.infrai_client import InfraiClient
from order_document_qa.order_qa_service import OrderQuestionService, QuestionRequest


class RecordingClient:
    def __init__(self) -> None:
        self.rerank_candidates: list[str] = []

    def embed(self, text: str, model: str) -> list[float]:
        return [0.2, 0.8]

    def query(
        self,
        collection: str,
        embedding: list[float],
        team_id: str,
        order_id: str,
        top_k: int,
    ) -> dict[str, Any]:
        return {
            "matches": [
                {
                    "metadata": {
                        "document_id": "receipt-41",
                        "document_type": "receipt",
                        "team_id": "team-ledger",
                        "order_id": "ord-41",
                        "text": "Receipt issued after checkout authorization.",
                    }
                },
                {
                    "metadata": {
                        "document_id": "update-foreign",
                        "document_type": "customer_update",
                        "team_id": "team-other",
                        "order_id": "ord-41",
                        "text": "Private update from another team.",
                    }
                },
            ]
        }

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict[str, Any]:
        self.rerank_candidates = candidates
        return {"results": [{"index": 0}]}


def test_answer_excludes_evidence_owned_by_another_team() -> None:
    client = RecordingClient()
    service = OrderQuestionService(cast(InfraiClient, client), "orders", "embedding-model")

    answer = service.answer(
        QuestionRequest(
            team_id="team-ledger",
            order_id="ord-41",
            question="Was the receipt issued?",
        )
    )

    assert answer.answer == "Receipt issued after checkout authorization."
    assert [item.document_id for item in answer.evidence] == ["receipt-41"]
    assert client.rerank_candidates == ["Receipt issued after checkout authorization."]
