# Approach

## Design

The evaluator rewards schema correctness, catalog grounding, and Recall@10, so the backend is intentionally deterministic at the boundary. `/chat` accepts only a full stateless message history. The service analyzes the conversation, decides whether to clarify, refuse, compare, or recommend, retrieves SHL catalog rows, validates URLs against the local catalog, and only then returns the fixed response schema. FastAPI docs and OpenAPI routes are disabled so the public API surface is limited to `/health` and `/chat`.

The catalog layer is built from SHL Product Catalog pages scoped to `type=1`, Individual Test Solutions. The scraper can run in fast list-only mode for full URL/name/test-type coverage, or detail mode to enrich rows with descriptions, duration, languages, job levels, and downloads. A seed catalog is included so cold starts and tests work even before a scrape. Rows named as packaged solutions or bundles are filtered at load time.

## Retrieval

The primary retriever is hybrid:

- lexical TF-IDF style ranking over assessment name, description, test type labels, job levels, language, and duration
- domain boosts for signals such as Java, stakeholder communication, OPQ, GSA, cognitive ability, personality, simulations, and graduate roles
- optional ChromaDB semantic retrieval using `sentence-transformers/all-MiniLM-L6-v2`

The runtime remains fast without a vector index because the lexical fallback is in-memory and deterministic. When a Chroma index exists, semantic scores are merged with lexical scores. Recommendation diversification ensures role-specific shortlists mix relevant test families, for example technical knowledge plus OPQ/GSA coverage when stakeholder behavior matters.

## Prompting

Gemini Flash is used for normal replies and Gemini Pro can be used for comparison wording. Prompts are deliberately short and only include the recent conversation plus retrieved catalog context. The LLM is never asked to emit JSON and never controls recommendation names or URLs. If Gemini is unavailable, the API falls back to grounded template replies, preserving the evaluator contract.

## Guardrails

The system refuses prompt injection, legal/salary advice, hacking, and unrelated hiring strategy. Vague first turns such as "I need an assessment" trigger one compact clarifying question. Comparison requests resolve names and known aliases such as `OPQ`, `OPQ32r`, and `GSA` to catalog rows before answering.

## Evaluation

Tests cover the hard API contract, strict Pydantic input validation, vague-query clarification, off-topic refusal, catalog-only recommendation URLs, and OPQ/GSA comparison behavior. `scripts/evaluate.py` replays realistic multi-turn traces for quick manual inspection. The request path avoids network scraping and embedding generation, keeping normal calls under the 30-second timeout.
