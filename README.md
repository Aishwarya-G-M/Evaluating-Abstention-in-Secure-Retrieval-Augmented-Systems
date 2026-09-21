# Evaluating Abstention in Secure Retrieval-Augmented Systems

An independent research project comparing vector-only RAG and GraphRAG when both systems operate behind the same secure LLM gateway.

## Research question

> On a curated set of high-risk and ambiguous queries, how does the rate of appropriate abstention or human escalation differ between GraphRAG combined with a secure LLM gateway and vector-only RAG combined with the same gateway?

The project investigates whether retrieval architecture affects a system's ability to recognise insufficient, conflicting, ambiguous, or potentially unsafe evidence and respond by abstaining or escalating rather than producing an unsupported answer.

## Motivation

Exploring how different GraphRAG functions in a given context when compared with a simple vector based RAG.
Keeping in mind a multi-agent system were multiple components work alongside, for future workings we can turn each one of the below mentioned paths to act at the capacity of an agent.

This project compares two retrieval paths while keeping the main security layer constant:

1. Vector-only RAG + secure LLM gateway.
2. GraphRAG + secure LLM gateway.

The goal is not to assume that GraphRAG is safer. The goal is to measure whether the two architectures exhibit different abstention behaviour, grounding quality, failure modes, and security–utility trade-offs.

## System components

### Vector-only RAG baseline

[Simple RAG Service](https://github.com/Aishwarya-G-M/simple-rag-service)

A FastAPI-based vector retrieval service for SMS spam and smishing analysis. It uses embedding-based retrieval over a labelled message corpus and passes retrieved context to an LLM for classification and explanation.

### GraphRAG experiments

[GraphRAG Fraud Experiments](https://github.com/Aishwarya-G-M/graphrag-fraud-experiments)

A research implementation for graph-based retrieval and fraud or smishing analysis. The experiments investigate whether entity and relationship structure provides useful evidence beyond nearest-neighbour vector retrieval.

### Shared security layer

[Secure LLM Gateway](https://github.com/Aishwarya-G-M/secure-llm-gateway)

A FastAPI-based gateway that inspects model inputs and outputs, applies centralised policies, and can block, redact, or route unsafe interactions for review. The gateway is intended to provide a common security boundary for both retrieval pipelines.

## Evaluation focus

The evaluation focuses on high-risk, ambiguous, adversarial, and insufficient-evidence queries rather than accuracy alone.

### Primary outcomes to evaluate

- Abstention rate.
- Human-escalation rate.
- Unsafe-answer rate.
- False-abstention rate.

## Threat model

The initial threat model includes:

- Prompt injection in user queries.
- Malicious or misleading retrieved content.
- Conflicting or incomplete evidence.
- Ambiguous messages requiring additional context.
- Attempts to induce unsupported classifications or explanations.
- Unsafe outputs that should be blocked, sanitised, or escalated.

The threat model will be refined as the evaluation cases and system integrations develop.

## Evaluation design

The comparison is intended to keep the following factors as consistent as practical:

- The underlying language model - the whole project uses groq free versions of models available
- The secure gateway and its policy configuration.
- The evaluation query set.
- The output schema and decision categories.
- The scoring and review procedure.

The retrieval approach is the primary independent variable. The evaluation will record not only whether the final classification is correct, but also whether the system selected an appropriate response mode: answer, abstain, or escalate.

## Decision categories

Each evaluated interaction should be assigned one of the following response categories:

- **Answer:** The available evidence is sufficient and the system provides a supported response.
- **Abstain:** The system identifies that the evidence is insufficient, conflicting, or unsafe for a reliable answer.
- **Escalate:** The system routes the case for human review because of risk, ambiguity, policy restrictions, or unresolved uncertainty.
- **Unsafe answer:** The system provides an unsupported, misleading, or policy-violating answer when it should have abstained or escalated.

The evaluation will distinguish appropriate abstention from over-refusal. A system that abstains on every query should not receive a high safety score.

## Current status

This is an ongoing project.
Work is still in progress to improvise in the above sections on the go as more evaluation sets are added.

Current work includes:

- Maintaining a vector RAG baseline for SMS spam and smishing analysis.
- Developing GraphRAG fraud and smishing experiments.
- Integrating both retrieval approaches with the secure LLM gateway.
- Defining high-risk and ambiguous evaluation cases.
- Implementing metrics for abstention, escalation, grounding, security, latency, and cost.

Results will be added after the evaluation protocol and integration are validated. No conclusion is currently being made about whether GraphRAG or vector-only RAG is safer.

## Planned next steps

1. Finalise the threat model and evaluation-case schema.
2. Validate the vector-only RAG baseline with the secure gateway.
3. Integrate and validate the GraphRAG pipeline under the same gateway configuration.
4. Run matched evaluations across both conditions.
5. Review ambiguous and high-risk cases using predefined labelling criteria.
6. Report aggregate results, failure modes, limitations, and recommended follow-up experiments.

## Scope and limitations

This is an independent engineering and evaluation project, not a claim that either retrieval architecture is generally safe. Early results may be specific to the selected spam and fraud corpora, model, gateway policies, graph-construction method, and evaluation cases.

The project will therefore report both positive and negative findings, including cases where GraphRAG adds complexity without improving abstention or grounding.

## Repository structure

```text
secure-rag-abstention-evaluation/
├── README.md
├── docs/
│   ├── research-question.md
│   ├── threat-model.md
│   └── evaluation-plan.md
├── evaluations/
│   ├── cases/
│   ├── configs/
│   └── metrics.py
└── results/
```

## Technologies

- Python
- FastAPI
- Vector embeddings and semantic retrieval
- Knowledge graphs and GraphRAG
- LLM-based classification and explanation
- Adversarial and security evaluation
- Automated metrics and experiment logging

## License

This project is currently under active development. Licensing and reproduction instructions will be added as the repository stabilises.

## References
Each individual repo documentation consists of the references and claims made.
