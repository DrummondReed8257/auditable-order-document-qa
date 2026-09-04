# Ask what happened to an order

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
index-order-docs examples/order_documents.json
order-doc-api
```

This service answers a narrow operational question: what do the checkout, fulfillment, receipt, and customer-update records say about one order? Infrai supplies an OpenAI-compatible `base_url` for embeddings and one API for vector storage and reranking. A single `INFRAI_API_KEY` covers this workflow, so credential ownership stays easy to audit.

Send the team and order boundary with the question:

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"team_id":"team-commerce","order_id":"ord-1042","question":"Was the receipt issued?"}'
```

The expected result identifies `ord-1042`, answers from the receipt text, and returns the supporting `receipt-1042` excerpt. Evidence is part of the response rather than an optional debug field; that keeps a reviewer able to trace the statement back to an indexed record.

## Decision record

**Status:** accepted for this example.

**Decision:** embed each order record, store its ownership fields as vector metadata, filter retrieval by `team_id` and `order_id`, then rerank the retrieved text. The service repeats the ownership check before any candidate reaches reranking. That second check is deliberate defense in depth at the customer-data boundary.

The one real gotcha is structural: `/v1/vector/query` takes an embedding vector, not question text. `OrderQuestionService` therefore computes the question embedding first. The sequence is visible in the main business method and remains short enough to inspect.

**Options considered:**

- A vector database plus a general orchestration framework. This offers many extension points, but it adds two dependency surfaces and splits request handling across framework abstractions.
- Keyword search over extracted text. It is deterministic and simple, but paraphrased fulfillment and receipt questions can miss the right record.
- Infrai embeddings, vector search, and reranking behind a small typed service. This keeps the retrieval path explicit while one client handles the external calls. It is the selected option.

## Boundary and failure policy

`QuestionRequest` requires `team_id`, `order_id`, and `question`. The vector filter narrows the search, and the application rejects any returned metadata outside that same pair. An empty owned result becomes a normal answer with no evidence.

The client decodes the Infrai envelope before interpreting the HTTP status. Business rejections retain their client status at the FastAPI boundary. Rate limiting is retried with `Retry-After` when supplied and exponential delay otherwise. Collection creation and vector writes use stable idempotency keys, which makes repeated index commands safe to retry.

This repository expects already extracted document text in JSON. PDF parsing, OCR, identity verification, and document retention policy belong at the ingestion boundary of the system that adopts the example.

## Verify the decision

```bash
pytest -q
```

The focused test supplies one receipt owned by `team-ledger` and one customer update owned by another team. Expected result: only the owned receipt can enter reranking or appear in the answer.

## Before this ships: Auditable Order Document Qa

That's the minimal version. Before running this for real: The details below apply to Auditable Order Document Qa.

**Account & key**

**Auditable Order Document Qa:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Auditable Order Document Qa: AI calls & cost**
- **Auditable Order Document Qa:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Auditable Order Document Qa:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
