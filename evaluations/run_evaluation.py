import csv
import json
import time
from pathlib import Path

import requests

GATEWAY_URL = "http://localhost:8000/evaluate-abstention"
GATEWAY_HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "key-abc123",  # Replace with your actual key.
}

QUERIES_FILE = (
    Path(__file__).parent
    / "queries"
    / "abstention_queries.jsonl"
)
OUTPUT_FILE = (
    Path(__file__).parent
    / "results"
    / "abstention_queries.jsonl"
)

BACKEND = "vector_rag"
TOP_K_VALUES = [25]
REQUEST_TIMEOUT_SECONDS = 60.0


def call_gateway(query: str, top_k: int) -> dict:
    response = requests.post(
        GATEWAY_URL,
        json={
            "query": query,
            "backend": BACKEND,
            "top_k": top_k,
        },
        headers=GATEWAY_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    print(
        f"[DEBUG] backend={BACKEND}, "
        f"top_k={top_k}, status={response.status_code}"
    )

    response.raise_for_status()
    data = response.json()
    print(f"[DEBUG] response_keys={list(data.keys())}")
    return data


def load_queries() -> list[dict]:
    queries = []

    with QUERIES_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                queries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}"
                ) from exc

    return queries


def main() -> None:
    queries = load_queries()
    results = []

    for query_record in queries:
        query_text = query_record["query"]
        query_id = query_record.get(
            "id",
            query_record.get("query_id", query_text[:40]),
        )

        for top_k in TOP_K_VALUES:
            started_at = time.perf_counter()

            try:
                response_data = call_gateway(query_text, top_k)
                model_response = response_data
                retrieval_metadata = response_data.get(
                    "retrieval_metadata",
                    {},
                )

                results.append({
                    "query_id": query_id,
                    "query": query_text,
                    "backend": BACKEND,
                    "top_k": top_k,
                    "abstention_status": model_response.get(
                        "abstention_status"
                    ),
                    "auxiliary_is_spam": model_response.get("is_spam"),
                    "answer": model_response.get("answer"),
                    "abstention_reason": model_response.get(
                        "abstention_reason"
                    ),
                    "requested_top_k": retrieval_metadata.get(
                        "requested_top_k"
                    ),
                    "actual_retrieved": retrieval_metadata.get(
                        "actual_retrieved"
                    ),
                    "context_chars": retrieval_metadata.get(
                        "context_chars"
                    ),
                    "latency_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2,
                    ),
                    "error": None,
                })

            except Exception as exc:
                print(
                    f"[ERROR] backend={BACKEND}, "
                    f"top_k={top_k}, query_id={query_id}, error={exc}"
                )

                results.append({
                    "query_id": query_id,
                    "query": query_text,
                    "backend": BACKEND,
                    "top_k": top_k,
                    "abstention_status": None,
                    "auxiliary_is_spam": None,
                    "answer": None,
                    "abstention_reason": None,
                    "requested_top_k": top_k,
                    "actual_retrieved": None,
                    "context_chars": None,
                    "latency_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2,
                    ),
                    "error": str(exc),
                })

    fieldnames = [
        "query_id",
        "query",
        "backend",
        "top_k",
        "abstention_status",
        "auxiliary_is_spam",
        "answer",
        "abstention_reason",
        "requested_top_k",
        "actual_retrieved",
        "context_chars",
        "latency_ms",
        "error",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
