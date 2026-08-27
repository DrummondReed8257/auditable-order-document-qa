from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .infrai_client import InfraiClient


def index_documents(path: Path) -> int:
    documents: list[dict[str, Any]] = json.loads(path.read_text())
    model = os.getenv("INFRAI_EMBEDDING_MODEL", "text-embedding-3-small")
    collection = os.getenv("INFRAI_COLLECTION", "commerce-order-documents")
    client = InfraiClient()
    try:
        vectors = []
        for document in documents:
            text = str(document["text"])
            embedding = client.embed(text, model)
            vectors.append(
                {
                    "id": str(document["document_id"]),
                    "values": embedding,
                    "metadata": {
                        "document_id": str(document["document_id"]),
                        "document_type": str(document["document_type"]),
                        "team_id": str(document["team_id"]),
                        "order_id": str(document["order_id"]),
                        "text": text,
                    },
                }
            )
        dimension = len(vectors[0]["values"])
        client.create_collection(collection, dimension)
        client.upsert(collection, vectors)
        return len(vectors)
    finally:
        client.close()


def run() -> None:
    parser = argparse.ArgumentParser(description="Index e-commerce order documents")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    count = index_documents(args.path)
    print(f"Indexed {count} order documents.")


if __name__ == "__main__":
    run()

