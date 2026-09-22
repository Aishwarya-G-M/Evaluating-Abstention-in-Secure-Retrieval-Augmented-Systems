import json
import csv
import requests
from pathlib import Path

GATEWAY_URL = "http://localhost:8000/chat"
GATEWAY_HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "key-abc123",  # your actual key
}

QUERIES_FILE = Path(__file__).parent / "abstention_queries_set2.jsonl"
OUTPUT_FILE = Path(__file__).parent / "abstention_results_set2.csv"

BACKENDS = ["vector_rag", "graph_rag"]

def call_gateway(prompt: str, backend: str) -> dict:
    resp = requests.post(
        GATEWAY_URL,
        json={"prompt": prompt, "backend": backend},
        headers=GATEWAY_HEADERS,
        timeout=30.0,
    )
    # Log status and raw text for debugging
    print(f"[DEBUG] backend={backend}, status={resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    print(f"[DEBUG] backend={backend}, keys={data.keys()}")
    return data

def main():
    queries = []
    with QUERIES_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))

    results = []

    for q in queries:
        query_text = q["query"]
        query_id = q.get("id", query_text[:40])

        for backend in BACKENDS:
            try:
                resp_data = call_gateway(query_text, backend)
            except Exception as e:
                print(f"[ERROR] backend={backend}, query_id={query_id}, error={e}")
                resp_data = {
                    "error": str(e),
                    "input_verdict": {},
                    "output_verdict": {},
                    "llm_output": "",
                }

            input_allowed = (
                resp_data.get("input_verdict") or {}
            ).get("allowed", None)

            output_allowed = (
                resp_data.get("output_verdict") or {}
            ).get("allowed", None)

            llm_output = resp_data.get("llm_output", "")

            results.append({
                "query_id": query_id,
                "query": query_text,
                "backend": backend,
                "input_allowed": input_allowed,
                "output_allowed": output_allowed,
                "llm_output": llm_output,
                "should_abstain_or_escalate": "",
                "abstain_or_escalate": "",
            })

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "query_id",
            "query",
            "backend",
            "input_allowed",
            "output_allowed",
            "llm_output",
            "should_abstain_or_escalate",
            "abstain_or_escalate",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} rows to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()