"""
Web interface for the VibeFinder Agent.

This is the command-line agent (`python -m src.main`) turned into an
actual webpage. It calls the exact same `RecommenderAgent` — the planner,
the Module 3 recommender, the evaluator, and the self-correcting retry —
so the web app and the CLI always behave identically.

Run it from the repo root:

    pip install -r requirements.txt
    streamlit run app.py
"""

import os
import tempfile

import streamlit as st

from src.agent import RecommenderAgent

st.set_page_config(page_title="VibeFinder Agent", page_icon="🎧", layout="centered")

EXAMPLES = [
    "upbeat pop for a workout",
    "chill lofi for studying",
    "some jazz",
    "romantic r&b",
    "asdf qwerty",
]


@st.cache_resource
def get_agent() -> RecommenderAgent:
    """Load the agent (and its catalog) once per server session."""
    return RecommenderAgent()


def render_result(result) -> None:
    """Render one AgentResult the same way the CLI prints it."""
    p = result.profile

    # What the agent understood.
    st.markdown(f"#### Request: *“{result.query or '(empty request)'}”*")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Genre", p.favorite_genre or "—")
    c2.metric("Mood", p.favorite_mood or "—")
    c3.metric("Energy", f"{p.target_energy}")
    c4.metric("Acoustic", "yes" if p.likes_acoustic else "no")

    # Confidence + status.
    st.progress(min(1.0, max(0.0, result.confidence)),
                text=f"Confidence {result.confidence:.2f}")
    left, right = st.columns(2)
    if result.passed:
        left.success("✓ Passed self-check")
    else:
        left.warning("⚠ Low confidence")
    right.info(f"{result.attempts} attempt{'s' if result.attempts > 1 else ''}")

    if result.advisory:
        st.warning(result.advisory)

    # Ranked recommendations.
    st.markdown("#### Recommendations")
    for rank, (song, score, explanation) in enumerate(result.recommendations, start=1):
        with st.container(border=True):
            top = st.columns([0.08, 0.72, 0.2])
            top[0].markdown(f"### {rank}")
            top[1].markdown(f"**{song['title']}**  \n{song['artist']}")
            top[2].markdown(f"### {score:.2f}")
            st.caption(f"because: {explanation}")

    # The agent's trace.
    with st.expander(f"Agent trace ({len(result.trace)} steps)"):
        for step in result.trace:
            st.markdown(f"- `{step}`")


def main() -> None:
    st.title("🎧 VibeFinder Agent")
    st.caption(
        "A self-checking music recommender. Type what you're in the mood for — "
        "the agent plans a taste profile, recommends songs, scores its own "
        "confidence, and retries when it isn't sure. Same engine as "
        "`python -m src.main`."
    )

    agent = get_agent()
    tab_text, tab_library = st.tabs(["💬 Type a request", "🎧 Apple Music library"])

    # --- Text request tab ---
    with tab_text:
        if "query" not in st.session_state:
            st.session_state.query = "chill lofi for studying"

        st.write("Try an example:")
        cols = st.columns(len(EXAMPLES))
        for col, example in zip(cols, EXAMPLES):
            label = example if len(example) <= 16 else example[:14] + "…"
            if col.button(label, key=f"ex_{example}", help=example):
                st.session_state.query = example

        query = st.text_input("Your request", key="query")
        if st.button("Recommend", type="primary") or query:
            render_result(agent.run(query))

    # --- Apple Music tab ---
    with tab_library:
        st.write(
            "Upload a library exported from the macOS Music app "
            "(**File → Library → Export Library…**), or use the bundled sample. "
            "No API key or Apple Developer account needed."
        )
        uploaded = st.file_uploader("Library.xml", type=["xml"])
        use_sample = st.button("Use bundled sample library")

        xml_path = None
        if uploaded is not None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
            tmp.write(uploaded.getvalue())
            tmp.close()
            xml_path = tmp.name
        elif use_sample:
            xml_path = os.path.join("data", "sample_library.xml")

        if xml_path:
            try:
                render_result(agent.run_from_library(xml_path))
            finally:
                if uploaded is not None and os.path.exists(xml_path):
                    os.unlink(xml_path)


if __name__ == "__main__":
    main()
