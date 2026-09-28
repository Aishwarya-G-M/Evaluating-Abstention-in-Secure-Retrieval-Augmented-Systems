from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml


BACKENDS = (
    "vector_rag",
    "graphrag",
)

GATEWAY_HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "key-abc123",
}


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if not isinstance(config, dict):
        raise ValueError(
            "Evaluation config must contain a YAML object"
        )

    return config


def load_queries(path: Path) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}: {exc}"
                ) from exc

            if isinstance(item, str):
                item = {"query": item}

            if not isinstance(item, dict):
                raise ValueError(
                    f"Line {line_number} must be a JSON object"
                )

            query = item.get("query")

            if not isinstance(query, str) or not query.strip():
                raise ValueError(
                    f"Line {line_number} is missing a non-empty query"
                )

            queries.append(item)

    return queries


def get_gateway_config(
    config: dict[str, Any],
) -> tuple[str, str, float]:
    gateway = config.get("gateway", config)

    if not isinstance(gateway, dict):
        raise ValueError(
            "The gateway configuration must be a YAML object"
        )

    base_url = (
        gateway.get("base_url")
        or gateway.get("url")
        or "http://127.0.0.1:8000"
    )

    path = (
        gateway.get("evaluation_path")
        or gateway.get("path")
        or "/evaluate-abstention"
    )

    timeout = float(
        gateway.get("timeout_seconds", 330)
    )

    return (
        str(base_url).rstrip("/"),
        str(path),
        timeout,
    )


def build_payload(
    backend: str,
    query_item: dict[str, Any],
) -> dict[str, Any]:
    query = query_item["query"]

    if backend == "vector_rag":
        return {
            "backend": "vector_rag",
            "query": query,
            "top_k": query_item.get("top_k", 25),
        }

    if backend == "graphrag":
        return {
            "backend": "graphrag",
            "query": query,
            "parameters": query_item.get(
                "parameters",
                {},
            ),
        }

    raise ValueError(
        f"Unsupported backend: {backend}"
    )


def call_gateway(
    gateway_url: str,
    gateway_path: str,
    timeout_seconds: float,
    backend: str,
    query_item: dict[str, Any],
) -> dict[str, Any]:
    url = (
        f"{gateway_url.rstrip('/')}"
        f"/{gateway_path.lstrip('/')}"
    )

    payload = build_payload(
        backend=backend,
        query_item=query_item,
    )

    started = time.perf_counter()

    try:
        response = requests.post(
            url,
            json=payload,
            headers=GATEWAY_HEADERS,
            timeout=timeout_seconds,
        )

        elapsed_ms = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

        try:
            response_body = response.json()
        except ValueError:
            response_body = {
                "raw_response": response.text,
            }

        return {
            "backend": backend,
            "query": query_item["query"],
            "request": payload,
            "http_status": response.status_code,
            "latency_ms": elapsed_ms,
            "response": response_body,
            "error": None
            if response.ok
            else response.text,
        }

    except requests.RequestException as exc:
        elapsed_ms = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

        return {
            "backend": backend,
            "query": query_item["query"],
            "request": payload,
            "http_status": None,
            "latency_ms": elapsed_ms,
            "response": None,
            "error": repr(exc),
        }


def evaluate(
    config_path: Path,
    queries_path: Path,
    output_path: Path,
) -> None:
    config = load_config(config_path)
    queries = load_queries(queries_path)

    gateway_url, gateway_path, timeout_seconds = (
        get_gateway_config(config)
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_started_at = datetime.now(
        timezone.utc
    ).isoformat()

    total_requests = 0

    with output_path.open("w", encoding="utf-8") as output_file:
        for query_index, query_item in enumerate(
            queries,
            start=1,
        ):
            for backend in BACKENDS:
                result = call_gateway(
                    gateway_url=gateway_url,
                    gateway_path=gateway_path,
                    timeout_seconds=timeout_seconds,
                    backend=backend,
                    query_item=query_item,
                )

                result["query_index"] = query_index
                result["run_started_at"] = run_started_at

                output_file.write(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                output_file.flush()

                total_requests += 1

                print(
                    f"[{query_index}/{len(queries)}] "
                    f"{backend}: "
                    f"HTTP {result['http_status']} "
                    f"{result['latency_ms']} ms",
                    flush=True,
                )

    print(
        f"Completed {total_requests} requests "
        f"for {len(queries)} queries across "
        f"{len(BACKENDS)} backends.",
        flush=True,
    )

    print(
        f"Results written to {output_path}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run every abstention query against "
            "vector RAG and GraphRAG."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "evaluations/configs/security_gateway.yaml"
        ),
    )

    parser.add_argument(
        "--queries",
        type=Path,
        default=Path(
            "evaluations/queries/abstention_queries.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "evaluations/results/dual_backend_results.jsonl"
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        evaluate(
            config_path=args.config,
            queries_path=args.queries,
            output_path=args.output,
        )
    except Exception as exc:
        print(
            f"Evaluation failed: {exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
