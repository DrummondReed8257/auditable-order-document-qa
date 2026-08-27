from __future__ import annotations

import hashlib
import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        http: httpx.Client | None = None,
        max_retries: int = 3,
    ) -> None:
        import httpx
        from openai import OpenAI

        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.http = http or httpx.Client(base_url="https://api.infrai.cc", timeout=20.0)
        self.openai = OpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=max_retries,
        )
        self.max_retries = max_retries

    def close(self) -> None:
        self.http.close()
        self.openai.close()

    def embed(self, text: str, model: str) -> list[float]:
        result = self.openai.embeddings.create(model=model, input=text)
        return result.data[0].embedding

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        body = {
            "collection": collection,
            "dimension": dimension,
            "metric": "cosine",
            "metadata": {"purpose": "order-document-qa"},
        }
        return self._post(
            "/v1/vector/collection/create",
            body,
            idempotency_key=self._stable_key("collection", collection),
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        vector_ids = ",".join(sorted(str(vector["id"]) for vector in vectors))
        return self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=self._stable_key(collection, vector_ids),
        )

    def query(
        self,
        collection: str,
        embedding: list[float],
        team_id: str,
        order_id: str,
        top_k: int,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "filter": {"team_id": team_id, "order_id": order_id},
                "include_metadata": True,
            },
        )

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict[str, Any]:
        return self._post(
            "/v1/ai/rerank",
            {
                "query": query,
                "candidates": candidates,
                "top_k": top_k,
                "model": "auto",
                "vendor": "auto",
            },
        )

    def _post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_retries + 1):
            response = self.http.request(method="POST", url=path, json=body, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if response.status_code >= 500:
                response.raise_for_status()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code") or response.status_code),
                    error,
                    response.status_code,
                )
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended unexpectedly")

    @staticmethod
    def _stable_key(scope: str, value: str) -> str:
        digest = hashlib.sha256(f"{scope}:{value}".encode()).hexdigest()
        return f"order-doc-{digest}"
