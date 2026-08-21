import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from rag import retrieve, load_and_split_documents


def test_documents_load_successfully():
    """Confirm all 3 runbooks are loaded and chunked."""
    chunks = load_and_split_documents()
    assert len(chunks) > 0, "No chunks were loaded from runbooks directory"

    sources = set(chunk.metadata["source"] for chunk in chunks)
    expected_sources = {
        "loki-alloy-404.md",
        "kubernetes-pod-crashloop.md",
        "suspicious-network-traffic.md"
    }
    assert sources == expected_sources, f"Expected {expected_sources}, got {sources}"


def test_retrieval_selects_correct_runbook_loki():
    """Loki-related query should retrieve the Loki runbook."""
    results = retrieve("Alloy cannot send logs to Loki, getting 404")
    assert len(results) > 0, "Expected at least one result above threshold"
    top_source = results[0][0].metadata["source"]
    assert top_source == "loki-alloy-404.md"


def test_retrieval_selects_correct_runbook_kubernetes():
    """Kubernetes-related query should retrieve the Kubernetes runbook."""
    results = retrieve("pod keeps restarting with CrashLoopBackOff")
    assert len(results) > 0, "Expected at least one result above threshold"
    top_source = results[0][0].metadata["source"]
    assert top_source == "kubernetes-pod-crashloop.md"


def test_retrieval_selects_correct_runbook_network():
    """SSH/network-related query should retrieve the network security runbook."""
    results = retrieve("seeing repeated failed SSH login attempts from one IP")
    assert len(results) > 0, "Expected at least one result above threshold"
    top_source = results[0][0].metadata["source"]
    assert top_source == "suspicious-network-traffic.md"


def test_unsupported_question_returns_no_results():
    """A completely unrelated question should return nothing above threshold."""
    results = retrieve("what's the best pizza topping combination")
    assert len(results) == 0, "Expected no results for an unrelated question"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

def test_retrieval_handles_rephrased_query():
    """A rephrased version of the SSH query should still retrieve the correct runbook."""
    results = retrieve("I am seeing repeated failed SSH login attempts from one IP address")
    assert len(results) > 0, "Expected retrieval to succeed on rephrased query"
    top_source = results[0][0].metadata["source"]
    assert top_source == "suspicious-network-traffic.md"    