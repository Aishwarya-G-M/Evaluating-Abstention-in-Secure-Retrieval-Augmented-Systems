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
    / "vector_rag_results.csv"
)

BACKEND = "vector_rag"
TOP_K_VALUES = [25]
REQUEST_TIMEOUT_SECONDS = 60.0
REQUEST_DELAY_SECONDS = 2.0

def classify_outcome(
    expected_behavior: str | None,
    actual_behavior: str | None,
) -> str | None:
    if expected_behavior is None or actual_behavior is None:
        return None

    if (
        expected_behavior == "abstain"
        and actual_behavior == "abstain"
    ):
        return "appropriate_abstention"

    if (
        expected_behavior == "abstain"
        and actual_behavior == "answer"
    ):
        return "unsupported_answer"

    if (
        expected_behavior == "answer"
        and actual_behavior == "answer"
    ):
        return "supported_answer"

    if (
        expected_behavior == "answer"
        and actual_behavior == "abstain"
    ):
        return "false_abstention"

    return "unknown"


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
                query_record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}"
                ) from exc

            if "query" not in query_record:
                raise ValueError(
                    f"Missing 'query' on line {line_number}"
                )

            queries.append(query_record)

    return queries

def classify_error(exc: Exception) -> str:
    error_text = str(exc).lower()

    if (
        "ratelimit" in error_text
        or "rate_limit" in error_text
        or "tokens per minute" in error_text
        or "429" in error_text
    ):
        return "rate_limit_exceeded"

    if "validationerror" in error_text or "invalid json" in error_text:
        return "invalid_model_output"

    return "request_failed"

def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    queries = load_queries()
    results = []

    for query_record in queries:
        query_text = query_record["query"]
        query_id = query_record.get(
            "id",
            query_record.get("query_id", query_text[:40]),
        )
        expected_behavior = query_record.get("expected_behavior")
        category = query_record.get("category")

        for top_k in TOP_K_VALUES:
            started_at = time.perf_counter()

            try:
                response_data = call_gateway(query_text, top_k)
                retrieval_metadata = response_data.get(
                    "retrieval_metadata",
                    {},
                )
                model_response = response_data
                actual_behavior = model_response.get(
                    "abstention_status"
                )
                evaluation_outcome = classify_outcome(
                    expected_behavior,
                    actual_behavior,
                )

                results.append({
                    "query_id": query_id,
                    "query": query_text,
                    "category": category,
                    "expected_behavior": expected_behavior,
                    "backend": BACKEND,
                    "top_k": top_k,
                    "abstention_status": actual_behavior,
                    "evaluation_outcome": evaluation_outcome,
                    "auxiliary_is_spam": model_response.get(
                        "is_spam"
                    ),
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
                error_type = classify_error(exc)

                print(
                    f"[ERROR] backend={BACKEND}, "
                    f"top_k={top_k}, query_id={query_id}, "
                    f"error_type={error_type}, error={exc}"
                )

                results.append({
                    "query_id": query_id,
                    "query": query_text,
                    "category": category,
                    "expected_behavior": expected_behavior,
                    "backend": BACKEND,
                    "top_k": top_k,
                    "abstention_status": None,
                    "evaluation_outcome": None,
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
                    "error": error_type,
                })
            finally:
                time.sleep(REQUEST_DELAY_SECONDS)

    fieldnames = [
        "query_id",
        "query",
        "category",
        "expected_behavior",
        "backend",
        "top_k",
        "abstention_status",
        "evaluation_outcome",
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
