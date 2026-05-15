# Prompt Strategy

The backend does not ask Gemini to produce the API JSON. The service retrieves
catalog rows first, validates every recommendation against the local SHL
catalog, then optionally asks Gemini Flash or Gemini Pro to write a concise
grounded reply over that retrieved context.

This keeps schema correctness and URL provenance deterministic while still
allowing natural conversational phrasing.

