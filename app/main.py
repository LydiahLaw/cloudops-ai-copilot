import time
from rag import retrieve, CHAT_MODEL
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

llm = ChatOllama(model=CHAT_MODEL, temperature=0)


class RemediationStep(BaseModel):
    instruction: str = Field(description="A concise restatement of a remediation step")
    evidence: str = Field(description="The exact sentence from the context supporting this step")


class IncidentAnswer(BaseModel):
    diagnosis: str
    steps: list[RemediationStep]


structured_llm = llm.with_structured_output(IncidentAnswer)

PROMPT_TEMPLATE = """You are an SRE assistant. Using the context below, explain the diagnosis and remediation steps.

If a step involves a command, copy an exact sentence directly from the context, word-for-word, into evidence. Do NOT write a description of the context — copy the actual sentence as it appears.

Correct evidence example: "Restart the Alloy service: `sudo systemctl restart alloy`"
Incorrect evidence example: "The context states that restarting is required"

Context:
{context}

Incident:
{query}
"""

COMMAND_MARKERS = ["kubectl ", "sudo ", "systemctl ", "docker ", "journalctl ", "curl "]


def normalize(text):
    return " ".join(text.split())


def contains_unsupported_command(instruction, evidence):
    for marker in COMMAND_MARKERS:
        if marker in instruction and marker not in evidence:
            return True
    return False


def answer_incident(query):
    results = retrieve(query)

    if not results:
        return {
            "answer": "I could not find sufficient guidance in the available runbooks.",
            "steps": [],
            "sources": []
        }

    context = "\n\n---\n\n".join([doc.page_content for doc, score in results])
    prompt = PROMPT_TEMPLATE.format(context=context, query=query)

    result = structured_llm.invoke(prompt)

    validated_steps = []
    for step in result.steps:
        evidence = step.evidence.strip()
        if evidence and normalize(evidence) in normalize(context) and not contains_unsupported_command(step.instruction, evidence):
            validated_steps.append({"instruction": step.instruction, "evidence": evidence})

    sources = []
    seen = set()
    for doc, score in results:
        key = (doc.metadata["source"], doc.page_content[:30])
        if key not in seen:
            seen.add(key)
            section = doc.page_content.split("\n")[0].replace("#", "").strip()
            sources.append({"source": doc.metadata["source"], "section": section})

    return {
        "answer": result.diagnosis,
        "steps": validated_steps,
        "sources": sources
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
        print(f"Diagnosis: {result['answer']}\n")
        print("Validated Steps:")
        for s in result['steps']:
            print(f"  - {s['instruction']}")
            print(f"    Evidence: \"{s['evidence']}\"")
        print("\nSources:")
        for s in result['sources']:
            print(f"  - {s['source']} — {s['section']}")