# API Contract

## `GET /health`

Response:

```json
{"status": "ok"}
```

## `POST /chat`

Request:

```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer"}
  ]
}
```

Response:

```json
{
  "reply": "Got it. Here are catalog-backed SHL assessments for the role.",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/products/product-catalog/view/java-8-new/",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

Notes:

- `recommendations` is empty while clarifying or refusing.
- recommendation items are always selected from the local SHL catalog.
- no server-side session state is stored.

