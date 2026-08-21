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

        if result.get("warning"):
            st.warning(result["warning"])
            if result["sources"]:
                with st.expander("📄 Retrieved sources"):
                    for s in result["sources"]:
                        st.markdown(f"- `{s['source']}`")
        else:
            st.subheader("Diagnosis")
            st.write(result["diagnosis"])

            st.subheader("Recommended Steps")
            for step in result["remediation_steps"]:
                st.markdown(f"- {step['instruction']}")

            if result["validation_steps"]:
                st.subheader("Validation")
                for step in result["validation_steps"]:
                    st.markdown(f"- {step['instruction']}")

            with st.expander("📄 Evidence used"):
                all_steps = result["remediation_steps"] + result["validation_steps"]
                for step in all_steps:
                    st.markdown(f"**Step:** {step['instruction']}")
                    st.markdown(f"> {step['evidence']}")
                    st.markdown(f"*Source: `{step['source']}` — {step['section']}*")
                    st.markdown("---")