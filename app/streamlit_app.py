import streamlit as st
from main import answer_incident

st.set_page_config(page_title="CloudOps AI Copilot", page_icon="🛠️")

st.title("🛠️ CloudOps AI Copilot")
st.caption("An AI-powered SRE incident assistant using RAG over sanitized runbooks. All incidents and runbooks are synthetic.")

incident = st.text_area(
    "Describe the incident:",
    placeholder="e.g. Alloy cannot send logs to Loki, getting 404"
)

if st.button("Diagnose", type="primary"):
    if not incident.strip():
        st.warning("Please describe an incident first.")
    else:
        with st.spinner("Analysing incident against runbooks..."):
            result = answer_incident(incident)

        st.subheader("Diagnosis")
        st.write(result["answer"])

        if result["steps"]:
            st.subheader("Recommended Steps")
            for step in result["steps"]:
                st.markdown(f"- {step['instruction']}")

        if result["sources"]:
            with st.expander("📄 Evidence used"):
                for step in result["steps"]:
                    st.markdown(f"**Step:** {step['instruction']}")
                    st.markdown(f"> {step['evidence']}")
                    st.markdown("---")
                st.markdown("**Sources:**")
                for s in result["sources"]:
                    st.markdown(f"- `{s['source']}` — {s['section']}")
        else:
            st.info("No supporting runbook sources found for this incident.")