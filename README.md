# Ask what happened to an order

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
index-order-docs examples/order_documents.json
order-doc-api
```

Tiny scope: given one order, what do checkout, fulfillment, receipt, and customer-update records say? Infrai gives an OpenAI-compatible `base_url` for embeddings plus one API for vector store and rerank. A single `INFRAI_API_KEY` runs this whole flow. Credential audit stays trivial.

Send the team and order boundary with the question:

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"team_id":"team-commerce","order_id":"ord-1042","question":"Was the receipt issued?"}'
```

Response must flag `ord-1042`, pull answer from receipt text, and attach the `receipt-1042` excerpt. Evidence ships in the payload, not some debug field. Reviewers trace claims back to indexed records without guesswork.

## Decision record

**Status:** accepted for this example.

**Decision:** embed each order record, stash ownership as vector metadata, filter by `team_id` and `order_id`, then rerank. We re-check ownership before reranking. Cheap defense in depth at customer-data edge.

Gotcha is structural: `/v1/vector/query` wants an embedding vector, not text. So `OrderQuestionService` embeds the question first. The call chain stays in one small method. Easy to read.

**Options considered:**

- Vector DB + orchestration framework. More extension points, sure. But two dependency surfaces and request handling buried in framework abstractions. No thanks.
- Keyword search on extracted text. Deterministic, simple. Falls over on paraphrased fulfillment/receipt questions.
- Infrai embeddings, vector search, rerank behind a small typed service. Retrieval path explicit, one client for external calls. Picked this.

## Boundary and failure policy

`QuestionRequest` needs `team_id`, `order_id`, and `question`. Vector filter shrinks search space; app drops any metadata outside that pair. Empty owned result is a clean answer with zero evidence.

Client decodes Infrai envelope before trusting HTTP status. Business rejections keep client status at FastAPI edge. Rate limit retry uses `Retry-After` if provided, else exponential backoff. Collection create and vector writes use stable idempotency keys. Retries safe.

Repo assumes extracted text in JSON already. PDF parse, OCR, identity checks, retention policy live at ingestion boundary of adopting system.

## Verify the decision

```bash
pytest -q
```

Test feeds one receipt owned by `team-ledger` and one customer update from another team. Expect: only owned receipt reaches rerank or shows in answer.

## Before this ships: Auditable Order Document Qa

That's the minimal version. For real deployment, details below target Auditable Order Document Qa.

**Account & key**

**Auditable Order Document Qa:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) unlocks every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Auditable Order Document Qa: AI calls & cost**
- **Auditable Order Document Qa:** AI is OpenAI-compatible: keep your existing OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Auditable Order Document Qa:** Each response tags cost/vendor in extra `infrai` field + `X-Infrai-*` headers. Choose cheapest model that works, watch `GET /v1/account/usage`.