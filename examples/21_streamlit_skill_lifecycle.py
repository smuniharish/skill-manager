"""Visual Skill lifecycle dashboard built with Streamlit."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from _streamlit_dashboard import SkillDashboard

from skill_manager import Skill, SkillLifecycleState

st.set_page_config(
    page_title="Skill Manager Lifecycle",
    page_icon="🧩",
    layout="wide",
)


@st.cache_resource
def dashboard() -> SkillDashboard:
    root = Path(os.getenv("SKILL_MANAGER_UI_SKILLS_DIR", "skills/streamlit"))
    return SkillDashboard(root)


def flash(kind: str, message: str) -> None:
    st.session_state["flash"] = (kind, message)


def show_flash() -> None:
    value = st.session_state.pop("flash", None)
    if value is not None:
        kind, message = value
        getattr(st, kind)(message)


def skill_label(skill: Skill) -> str:
    return f"{skill.metadata.name} · {skill.metadata.version} · " f"{skill.lifecycle.state.value}"


service = dashboard()

st.title("Skill Manager lifecycle console")
st.caption(
    "Generate, validate, inspect, approve, and reject Skills through public " "skill-manager APIs."
)
show_flash()

try:
    skills = service.skills()
    counts = service.counts()
    documents = service.source_documents()
except Exception as error:
    st.error(f"Catalog loading failed: {type(error).__name__}: {error}")
    st.stop()

columns = st.columns(5)
columns[0].metric("Registered", len(skills))
columns[1].metric("Active", counts[SkillLifecycleState.ACTIVE])
columns[2].metric("Pending approval", counts[SkillLifecycleState.PENDING_APPROVAL])
columns[3].metric("Rejected", counts[SkillLifecycleState.REJECTED])
columns[4].metric("Persisted YAML", len(documents))

if service.manager.source_errors:
    st.error("One or more Skill documents failed validation while loading.")
    st.json(dict(service.manager.source_errors))
else:
    st.success("Catalog and persisted YAML loaded without validation errors.")

catalog_tab, generate_tab, validate_tab, feedback_tab = st.tabs(
    ("Catalog & review", "Create or generate", "Validate & load", "Feedback audit")
)

with catalog_tab:
    left, right = st.columns((1, 2))
    with left:
        state_filter = st.multiselect(
            "Lifecycle state",
            [state.value for state in SkillLifecycleState],
            default=[state.value for state in SkillLifecycleState],
        )
        visible = [skill for skill in skills if skill.lifecycle.state.value in state_filter]
        selected = st.selectbox(
            "Registered Skill",
            visible,
            format_func=skill_label,
            index=0 if visible else None,
        )
        if st.button("Reload persisted Skills", use_container_width=True):
            try:
                service.refresh()
                flash("success", "Persisted Skill documents reloaded and validated.")
                st.rerun()
            except Exception as error:
                st.error(f"Reload failed: {type(error).__name__}: {error}")

    with right:
        if selected is None:
            st.info("No Skills match the selected lifecycle states.")
        else:
            state = selected.lifecycle.state
            if state is SkillLifecycleState.ACTIVE:
                st.success("ACTIVE — available for discovery and bundle composition")
            elif state is SkillLifecycleState.PENDING_APPROVAL:
                st.warning("PENDING_APPROVAL — blocked until a human decision")
            else:
                st.error("REJECTED — retained for audit and revision")

            st.subheader(selected.metadata.name)
            st.write(selected.metadata.description)
            detail_tabs = st.tabs(("Validated model", "Canonical YAML", "Governance"))
            with detail_tabs[0]:
                st.json(selected.model_dump(mode="json"))
            with detail_tabs[1]:
                st.code(service.yaml(selected), language="yaml")
            with detail_tabs[2]:
                st.json(
                    {
                        "origin": selected.provenance.origin.value,
                        "source": selected.provenance.source,
                        "state": selected.lifecycle.state.value,
                        "reviewer": selected.governance.reviewer,
                        "reason": selected.governance.reason,
                        "approval_event_id": selected.governance.approval_event_id,
                        "rejection_event_id": selected.governance.rejection_event_id,
                    }
                )

            if state is SkillLifecycleState.PENDING_APPROVAL:
                st.divider()
                reviewer = st.text_input("Reviewer", value="developer")
                approve_column, reject_column = st.columns(2)
                with approve_column:
                    approval_reason = st.text_area(
                        "Approval reason",
                        value="Instructions and metadata verified.",
                    )
                    if st.button(
                        "Approve Skill",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            service.approve(
                                selected.skill_id,
                                reviewer=reviewer,
                                reason=approval_reason,
                            )
                            flash("success", f"Approved {selected.metadata.name}.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"Approval failed: {type(error).__name__}: {error}")
                with reject_column:
                    rejection_feedback = st.text_area(
                        "Required correction",
                        placeholder="Explain exactly what must change.",
                    )
                    if st.button("Reject Skill", use_container_width=True):
                        try:
                            service.reject(
                                selected.skill_id,
                                reviewer=reviewer,
                                feedback=rejection_feedback,
                            )
                            flash("warning", f"Rejected {selected.metadata.name}.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"Rejection failed: {type(error).__name__}: {error}")

with generate_tab:
    manual_tab, llm_tab = st.tabs(("Manual candidate", "Real LLM generation"))
    with manual_tab:
        with st.form("manual-skill"):
            name = st.text_input("Name", value="incident-triage")
            version = st.text_input("Version", value="1.0.0")
            description = st.text_area(
                "Description",
                value="Triage production incidents using verified evidence.",
            )
            instructions = st.text_area(
                "Instructions (one per line)",
                value=(
                    "Collect observable symptoms before proposing causes.\n"
                    "Separate confirmed facts from hypotheses.\n"
                    "Escalate when evidence is insufficient."
                ),
            )
            tags = st.text_input("Tags (comma separated)", value="operations,production")
            submitted = st.form_submit_button(
                "Create pending candidate",
                type="primary",
                use_container_width=True,
            )
        if submitted:
            try:
                created = service.create_candidate(
                    name=name,
                    version=version,
                    description=description,
                    instructions=tuple(
                        line.strip() for line in instructions.splitlines() if line.strip()
                    ),
                    tags=tuple(tag.strip() for tag in tags.split(",") if tag.strip()),
                )
                flash(
                    "success",
                    f"Created {created.metadata.name}; human approval is required.",
                )
                st.rerun()
            except Exception as error:
                st.error(f"Candidate creation failed: {type(error).__name__}: {error}")

    with llm_tab:
        api_key = os.getenv("EXPLABS_API_KEY", "")
        if api_key:
            st.success("Hosted model credential detected from the environment.")
        else:
            st.warning("Set EXPLABS_API_KEY before using live generation.")
        with st.form("llm-skill"):
            request = st.text_area(
                "Generation request",
                value=(
                    "Create a Skill named api-incident-review version 1.0.0. "
                    "It must review API incidents, distinguish evidence from "
                    "hypotheses, and require no external capabilities."
                ),
                height=140,
            )
            model = st.text_input(
                "Model",
                value=os.getenv("SKILL_MANAGER_MODEL", "gpt-5.6-luna"),
            )
            base_url = st.text_input(
                "OpenAI-compatible base URL",
                value=os.getenv(
                    "SKILL_MANAGER_LLM_BASE_URL",
                    "https://api.experientiallabs.ai/v1",
                ),
            )
            generate = st.form_submit_button(
                "Generate and validate candidate",
                type="primary",
                use_container_width=True,
                disabled=not api_key,
            )
        if generate:
            try:
                with st.spinner("Generating and validating canonical Skill data..."):
                    created = service.generate_candidate(
                        request=request,
                        api_key=api_key,
                        model=model,
                        base_url=base_url,
                    )
                flash(
                    "success",
                    f"Generated {created.metadata.name}; human approval is required.",
                )
                st.rerun()
            except Exception as error:
                st.error(f"Generation failed: {type(error).__name__}: {error}")

with validate_tab:
    default_document = service.yaml(skills[0]) if skills else ""
    document = st.text_area(
        "Canonical Skill YAML",
        value=default_document,
        height=420,
    )
    validate_column, import_column = st.columns(2)
    with validate_column:
        if st.button("Validate only", use_container_width=True):
            try:
                validated = service.validate_yaml(document)
                st.success(
                    f"Valid Skill: {validated.metadata.name} " f"{validated.metadata.version}"
                )
                st.json(validated.model_dump(mode="json"))
            except Exception as error:
                st.error(f"Validation failed: {type(error).__name__}: {error}")
    with import_column:
        if st.button("Validate and register", type="primary", use_container_width=True):
            try:
                imported = service.import_yaml(document)
                flash(
                    "success",
                    f"Validated and registered {imported.metadata.name}.",
                )
                st.rerun()
            except Exception as error:
                st.error(f"Import failed: {type(error).__name__}: {error}")

with feedback_tab:
    skill_filter = st.selectbox(
        "Feedback target",
        [None, *skills],
        format_func=lambda value: "All Skills" if value is None else skill_label(value),
    )
    feedback = service.feedback_events(None if skill_filter is None else skill_filter.skill_id)
    if feedback:
        st.dataframe(
            [
                {
                    "feedback_id": event["feedback_id"],
                    "category": event["category"],
                    "status": event["status"],
                    "target_id": event["target"]["id"],
                    "updated_at": event["updated_at"],
                }
                for event in feedback
            ],
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("Full feedback records"):
            st.json(feedback)
    else:
        st.info("No approval or rejection feedback has been recorded yet.")
