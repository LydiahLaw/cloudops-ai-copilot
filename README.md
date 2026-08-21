# CloudOps AI Copilot

An AI-powered SRE incident assistant that uses Retrieval-Augmented Generation (RAG) to diagnose infrastructure incidents against a set of operational runbooks, with citations grounded in retrieved document metadata rather than model claims.

Built as a portfolio project demonstrating RAG architecture, local LLM deployment, structured output validation, and honest handling of small-model limitations.

---

## Table of Contents

1. [Problem Being Solved](#problem-being-solved)
2. [Architecture](#architecture)
3. [AI / RAG Workflow](#ai--rag-workflow)
4. [Technologies Used](#technologies-used)
5. [Security Decisions](#security-decisions)
6. [Installation Instructions](#installation-instructions)
7. [Example Input and Output](#example-input-and-output)
8. [Known Limitations](#known-limitations)
9. [Future Improvements](#future-improvements)
10. [Cost-Conscious Cleanup Instructions](#cost-conscious-cleanup-instructions)
11. [Synthetic Data Statement](#synthetic-data-statement)

---

## Problem Being Solved

SRE and DevOps teams rely on runbooks to diagnose recurring infrastructure incidents, but manually searching documentation during an active incident is slow. This project explores whether a small, locally-run LLM combined with a RAG pipeline can:

- Retrieve the correct runbook for a described incident
- Generate a diagnosis grounded strictly in that runbook's content
- Cite the exact source used, verified against retrieval metadata rather than trusting the model's own claims
- Safely decline to answer when no runbook covers the incident

The scenarios modeled here (Grafana Alloy → Loki log shipping failures, Kubernetes pod crash loops, suspicious network traffic) are inspired by real production troubleshooting patterns.

---

## Architecture

```
Markdown runbooks
       ↓
LangChain document loader (DirectoryLoader + TextLoader)
       ↓
LangChain text splitter (RecursiveCharacterTextSplitter)
       ↓
Ollama embeddings (nomic-embed-text)
       ↓
ChromaDB vector store
       ↓
User incident → similarity search with relevance scoring
       ↓
Retrieval-score gating (threshold-based accept/reject)
       ↓
Retrieved context + constrained prompt
       ↓
Ollama LLM (qwen2.5:1.5b-instruct) with structured output
       ↓
Python-side evidence validation against source context
       ↓
Diagnosis + validated remediation steps + metadata-based citations
```

**Key design principle:** the accept/reject decision for "is this incident covered by our runbooks?" is made entirely by the deterministic retrieval-score threshold, never by the LLM's own judgment. This was a deliberate architectural correction made after testing (see [Known Limitations](#known-limitations)).

---

## AI / RAG Workflow

1. **Chunking:** Each runbook is split into overlapping chunks (500 chars, 50 overlap) along markdown section boundaries, so retrieval can return a specific section (e.g., "Remediation") rather than a whole document.
2. **Embedding:** Each chunk is embedded using `nomic-embed-text`, a small local embedding model run via Ollama.
3. **Retrieval:** A user's incident description is embedded and compared against stored chunks using cosine similarity. The top 2 chunks are returned, filtered by a minimum relevance score.
4. **Grounded generation:** Retrieved chunks are passed as context to `qwen2.5:1.5b-instruct`, which is prompted to produce a diagnosis and remediation steps, with each step required to include an exact supporting sentence copied from the context.
5. **Evidence validation:** Every "evidence" string the model returns is checked in Python against the actual retrieved context (whitespace-normalized substring match). Steps whose evidence cannot be verified — or which introduce a command not present in their own evidence — are silently dropped rather than shown to the user.
6. **Citation display:** Sources shown to the user come from retrieval metadata (filename + section heading), never from the model naming a document itself.

---

## Technologies Used

| Component | Tool |
|---|---|
| Orchestration | LangChain (basic pipeline only — no LangGraph, no agents) |
| Vector store | ChromaDB |
| Embedding model | Ollama — `nomic-embed-text` |
| Chat model | Ollama — `qwen2.5:1.5b-instruct` |
| Structured output | Pydantic + LangChain's `with_structured_output` |
| Interface | Streamlit |
| Testing | pytest |
| Language | Python 3.12 |
| Environment | WSL2 (Ubuntu) |

**Containerization (Docker):** planned but deferred — see [Known Limitations](#known-limitations).

---

## Security Decisions

- **No real infrastructure data:** all runbooks and sample incidents are synthetic or generalized from patterns, containing no real hostnames, IPs, credentials, or company-specific details.
- **No agentic/autonomous actions:** the system only diagnoses and recommends — it never executes commands, modifies infrastructure, or calls external APIs. This was a deliberate scope decision (no LangGraph, no agent framework) to keep the system observable and safe.
- **Evidence validation as a security control, not just an accuracy control:** by requiring every remediation step to be traceable to verbatim source text, the system prevents the model from fabricating commands that could be harmful if acted upon by a human operator without verification.
- **Command-marker filtering:** any generated instruction containing command-like text (`kubectl `, `sudo `, `systemctl `, `docker `, `journalctl `, `curl `) is only accepted if that exact command also appears in its cited evidence — preventing the model from inventing plausible-but-fabricated commands.
- **No secrets in the repository:** no API keys, credentials, or `.env` files are committed (see `.gitignore` and `.env.example`).

---

## Installation Instructions

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/download) installed locally

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd cloudops-ai-copilot

# Pull required models
ollama pull qwen2.5:1.5b-instruct
ollama pull nomic-embed-text

# Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app/streamlit_app.py
```

The app will open at `http://localhost:8501`.

### Running tests

```bash
pytest tests/test_rag.py -v
```

---

## Example Input and Output

**Input:**
```
Alloy cannot send logs to Loki, getting 404
```

**Output:**

> **Diagnosis:** The symptoms indicate that the logs are failing to be pushed to Loki due to a 404 error. This suggests that the Loki endpoint in the Alloy configuration is incorrect or missing.
>
> **Recommended Steps:**
> - Restart the Alloy service: `sudo systemctl restart alloy`
>
> **Evidence used:**
> - *"Restart the Alloy service: `sudo systemctl restart alloy`"*
>
> **Sources:**
> - `loki-alloy-404.md` — Runbook: Alloy Cannot Send Logs to Loki (HTTP 404)
> - `loki-alloy-404.md` — Remediation

**Unsupported question example:**

Input: `What's the best pizza topping combination`

Output: *"I could not find sufficient guidance in the available runbooks."* — correctly and consistently rejected across repeated testing, with no sources shown.

*(Screenshots of the running Streamlit app are included separately in the repository.)*

---

## Known Limitations

This project surfaced several real, instructive limitations through hands-on testing — documented honestly rather than hidden, since understanding *why* something fails is as valuable as making it work:

1. **Model selection mattered significantly.** The initial model, `llama3.2:1b`, exhibited two failure modes: it sometimes hallucinated plausible-but-fabricated commands (e.g., inventing `kubectl restart cluster`, which doesn't exist) even when instructed not to, and it later began refusing to answer entirely once the prompt included security/incident-response framing — likely triggering overly broad built-in safety guardrails misapplied to benign defensive SRE content. Switching to `qwen2.5:1.5b-instruct` resolved both issues while remaining small enough to run on limited hardware (8GB RAM).

2. **The LLM's own relevance judgment proved non-deterministic.** An earlier design asked the model to output a `supported: true/false` field alongside its answer, intended as a second layer of relevance gating. Testing showed this field flipped between `True` and `False` across identical repeated queries at `temperature=0`, a known characteristic of CPU-based local inference. The final design removed this entirely and relies solely on the deterministic retrieval-score threshold for the accept/reject decision — the LLM is only ever asked to generate from context already confirmed relevant.

3. **The retrieval relevance threshold required empirical tuning.** An initial threshold of 0.60 caused a rephrased but valid version of the SSH brute-force query to incorrectly fall back to "no guidance found," scoring 0.593 — just below cutoff. Lowering the threshold to 0.55 fixed this specific case (verified consistent across repeated runs) without causing the deliberately unrelated test question ("best pizza topping combination") to incorrectly pass. This reflects a genuine precision/recall tradeoff inherent to threshold-based retrieval gating, not a bug to be fully eliminated.

4. **Evidence-field compliance required prompt iteration.** Early prompt versions caused the model to write descriptions *about* the context (e.g., "The context states that restarting is required") rather than copying an exact sentence *from* the context into the evidence field — which correctly failed Python-side validation, but also meant every step was silently dropped. Adding a right/wrong contrastive example to the prompt fixed this reliably.

5. **Docker containerization was deferred**, not skipped from lack of understanding. Testing showed the local WSL2 environment had only ~2GB of available RAM after running Ollama — insufficient headroom to also run Docker Desktop's background VM without risking system instability. A working `Dockerfile` is included in the repository; building and testing it is a documented next step for an environment with adequate resources (e.g., a cloud VM or CI runner).

6. **Small local models occasionally produce minor unverified elaboration** even after the fixes above — for example, restating a real step in slightly generalized language. The evidence-validation layer specifically catches and drops any step containing a command not present in its cited evidence; free-text diagnosis prose is not independently fact-checked. This is a known tradeoff of relying on a 1.5B-parameter model for generation, not a failure of the RAG architecture itself — retrieval accuracy was 100% reliable and fully covered by automated tests throughout development.

---

## Future Improvements

- Test and validate the included `Dockerfile` in an environment with more available memory (cloud VM or GitHub Actions runner)
- Expand the runbook set beyond the current 3 scenarios
- Add a lightweight automated evaluation script that runs the full test-question table (see below) end-to-end through `answer_incident()`, not just through `retrieve()`, to track generation-layer accuracy over time
- Evaluate a mid-sized model (7B class) to assess whether the remaining minor elaboration issue improves meaningfully, if hardware allows
- Add per-step confidence scoring surfaced in the UI, not just a binary validated/dropped decision

---

## Cost-Conscious Cleanup Instructions

This project runs entirely locally with no cloud costs incurred:

- All models (`qwen2.5:1.5b-instruct`, `nomic-embed-text`) run via Ollama on local hardware — no API usage fees
- No cloud resources were provisioned for this MVP
- To remove local resources: `ollama rm qwen2.5:1.5b-instruct nomic-embed-text` and delete the `chroma_db/` directory
- If the deferred Docker/cloud deployment step is completed later, ensure any provisioned cloud resources (e.g., EC2, S3) are torn down after testing to avoid ongoing charges

---

## Synthetic Data Statement

All runbooks, incident descriptions, and test queries used in this project are synthetic or generalized from publicly known troubleshooting patterns. No real production logs, IP addresses, hostnames, credentials, or company-specific infrastructure details appear anywhere in this repository.