import os
import re
import time
from rag import retrieve, CHAT_MODEL, RUNBOOKS_DIR
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

llm = ChatOllama(model=CHAT_MODEL, temperature=0)


class IncidentAnswer(BaseModel):
    diagnosis: str = Field(
        description="A brief description of the incident and likely cause. Do not include commands or remediation instructions."
    )


structured_llm = llm.with_structured_output(IncidentAnswer)

DIAGNOSIS_PROMPT = """You are an SRE assistant.

Below is the relevant runbook content:

{context}

Incident:
{query}

Write a short diagnosis of no more than two sentences describing the problem and likely cause. Do not include commands, remediation instructions, URLs, or procedural steps.

Answer:"""

DIAGNOSIS_MARKERS = ["kubectl ", "sudo ", "systemctl ", "docker ", "journalctl ", "curl ", "http://", "https://"]


def normalize_section(section):
    section = section.strip().lower()
    if section in {"remediation", "remediation steps"}:
        return "Remediation"
    if section in {"validation", "validation steps", "verification"}:
        return "Validation"
    if section in {"symptoms", "observed symptoms"}:
        return "Symptoms"
    if section in {"likely causes", "causes", "root cause"}:
        return "Likely Causes"
    return section.title()


def clean_markdown_step(text):
    return re.sub(r"^(?:[-*]\s+|\d+\.\s+)", "", text).strip()


def build_evidence_map_from_full_file(source_filename):
    """Load the ENTIRE selected runbook from disk (not just top-k retrieved chunks),
    so remediation/validation steps are never missed due to chunking or top-k limits."""
    filepath = os.path.join(RUNBOOKS_DIR, source_filename)
    evidence_map = {}
    counter = 1
    current_section = "Unknown"

    with open(filepath, "r") as f:
        lines = f.read().splitlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            current_section = normalize_section(line.lstrip("#").strip())
            continue
        if line.startswith("#"):
            continue
        eid = f"S{counter}"
        evidence_map[eid] = {"text": line, "source": source_filename, "section": current_section}
        counter += 1

    return evidence_map


def extract_actionable_steps(evidence_map):
    """Deterministic extraction — no LLM selection involved, so results are identical
    on every run regardless of model non-determinism."""
    remediation_steps = []
    validation_steps = []

    for eid, entry in evidence_map.items():
        step = {
            "instruction": clean_markdown_step(entry["text"]),
            "evidence": entry["text"],
            "evidence_id": eid,
            "source": entry["source"],
            "section": entry["section"],
        }
        if entry["section"] == "Remediation":
            remediation_steps.append(step)
        elif entry["section"] == "Validation":
            validation_steps.append(step)

    return remediation_steps, validation_steps


def diagnosis_contains_actionable_content(diagnosis):
    lowered = diagnosis.lower()
    return any(marker in lowered for marker in DIAGNOSIS_MARKERS)


def safe_diagnosis(diagnosis):
    if diagnosis_contains_actionable_content(diagnosis):
        return "The incident appears related to the configuration described in the retrieved runbook."
    return diagnosis


def answer_incident(query):
    results = retrieve(query)

    if not results:
        return {
            "diagnosis": None,
            "remediation_steps": [],
            "validation_steps": [],
            "sources": [],
            "warning": "I could not find sufficient guidance in the available runbooks."
        }

    # Identify the single best-matching runbook and load it fully, rather than
    # relying only on the top-k retrieved chunks (which may miss Remediation/Validation
    # content if a Symptoms chunk happened to score highest).
    selected_source = results[0][0].metadata.get("source", "unknown")
    evidence_map = build_evidence_map_from_full_file(selected_source)

    remediation_steps, validation_steps = extract_actionable_steps(evidence_map)

    sources = [{"source": selected_source, "section": "Remediation"}] if remediation_steps else []

    if not remediation_steps:
        return {
            "diagnosis": None,
            "remediation_steps": [],
            "validation_steps": [],
            "sources": sources,
            "warning": "The relevant runbook was retrieved, but no remediation instructions were found. Review the cited runbook directly."
        }

    context = "\n\n---\n\n".join([doc.page_content for doc, score in results])
    prompt = DIAGNOSIS_PROMPT.format(context=context, query=query)

    try:
        result = structured_llm.invoke(prompt)
        diagnosis = safe_diagnosis(result.diagnosis.strip())
    except Exception:
        diagnosis = "The incident appears related to the configuration described in the retrieved runbook."

    return {
        "diagnosis": diagnosis,
        "remediation_steps": remediation_steps,
        "validation_steps": validation_steps,
        "sources": sources,
        "warning": None
    }


if __name__ == "__main__":
    test_queries = [
        "Alloy cannot send logs to Loki, getting 404",
        "pod keeps restarting with CrashLoopBackOff",
        "seeing repeated failed SSH login attempts from one IP",
        "what's the best pizza topping combination"
    ]

    for q in test_queries:
        print(f"\nCalling model for: {q}")
        start = time.time()
        result = answer_incident(q)
        elapsed = time.time() - start
        print(f"(took {elapsed:.1f}s)\n")

        print(f"{'='*60}")
        print(f"Incident: {q}\n")

        if result.get("warning"):
            print(f"WARNING: {result['warning']}\n")
        else:
            print(f"Diagnosis: {result['diagnosis']}\n")
            print("Remediation Steps:")
            for s in result['remediation_steps']:
                print(f"  - {s['instruction']}")
            print("\nValidation Steps:")
            for s in result['validation_steps']:
                print(f"  - {s['instruction']}")

        print("\nSources:")
        for s in result['sources']:
            print(f"  - {s['source']} — {s['section']}")