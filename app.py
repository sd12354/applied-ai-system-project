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

import html
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

# --- Neon / synthwave styling -------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root{
  --magenta:#ff2d95; --purple:#a855f7; --cyan:#22d3ee; --violet:#7c3aed;
  --ink:#f3edff; --muted:#b3a7d6; --line:rgba(168,85,247,.22);
  --card:rgba(255,255,255,.035); --grad:linear-gradient(90deg,#ff2d95,#a855f7 55%,#22d3ee);
}

/* page background: deep gradient + soft glows */
.stApp{
  background:
    radial-gradient(1100px 620px at 12% -8%, rgba(255,45,149,.20), transparent 60%),
    radial-gradient(1000px 680px at 92% 8%, rgba(34,211,238,.16), transparent 60%),
    radial-gradient(900px 900px at 50% 120%, rgba(124,58,237,.22), transparent 55%),
    linear-gradient(180deg,#140a28 0%,#0d0820 55%,#06040f 100%);
  background-attachment: fixed;
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"]{ background:transparent; }
[data-testid="stToolbar"]{ right:12px; }
.block-container{ padding-top:2.2rem; padding-bottom:4rem; max-width:820px; }
html, body, [class*="st-"]{ font-family:'Inter',system-ui,sans-serif; }

/* hero */
.vf-eyebrow{
  font-family:'Space Grotesk',sans-serif; text-transform:uppercase; letter-spacing:.26em;
  font-size:.72rem; font-weight:600; color:var(--cyan); margin:0 0 10px;
}
.vf-title{
  font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:clamp(2.1rem,6vw,3rem);
  line-height:1.02; margin:0 0 10px; letter-spacing:-.02em;
  background:linear-gradient(92deg,#fff 10%,#ffd1ec 30%,#ff2d95 52%,#a855f7 72%,#22d3ee 96%);
  -webkit-background-clip:text; background-clip:text; color:transparent;
  text-shadow:0 0 40px rgba(255,45,149,.25);
}
.vf-sub{ color:var(--muted); font-size:1rem; max-width:60ch; margin:0 0 4px; }
.vf-sub code{ background:rgba(124,58,237,.22); color:#e9d5ff; padding:.08em .4em; border-radius:6px; font-size:.86em; }

/* tabs */
[data-baseweb="tab-list"]{ gap:6px; background:transparent; border-bottom:1px solid var(--line); }
button[data-baseweb="tab"]{ font-family:'Space Grotesk',sans-serif; font-weight:600; color:var(--muted); }
button[data-baseweb="tab"][aria-selected="true"]{ color:#fff; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"]{ background:var(--magenta)!important; height:3px!important; }

/* text input */
[data-testid="stTextInput"] input{
  background:rgba(255,255,255,.05)!important; color:var(--ink)!important;
  border:1.5px solid var(--line)!important; border-radius:13px!important;
  padding:14px 16px!important; font-size:1rem!important;
}
[data-testid="stTextInput"] input:focus{
  border-color:var(--magenta)!important; box-shadow:0 0 0 3px rgba(255,45,149,.22)!important;
}
[data-testid="stTextInput"] label, [data-testid="stFileUploader"] label{ color:var(--muted)!important; font-weight:600; }

/* buttons: primary = gradient, secondary = neon outline */
.stButton>button{
  font-family:'Space Grotesk',sans-serif; font-weight:600; border-radius:999px;
  transition:transform .12s ease, box-shadow .12s ease, border-color .12s;
}
[data-testid="stBaseButton-primary"], .stButton>button[kind="primary"]{
  background:var(--grad)!important; color:#fff!important; border:none!important;
  box-shadow:0 8px 24px rgba(255,45,149,.35); padding:.55rem 1.6rem!important;
}
[data-testid="stBaseButton-primary"]:hover{ transform:translateY(-1px); box-shadow:0 10px 30px rgba(255,45,149,.5); }
[data-testid="stBaseButton-secondary"], .stButton>button[kind="secondary"]{
  background:rgba(255,255,255,.04)!important; color:var(--ink)!important;
  border:1px solid var(--line)!important;
}
[data-testid="stBaseButton-secondary"]:hover{ border-color:var(--cyan)!important; color:var(--cyan)!important; }

/* profile chips */
.vf-profile{ display:flex; flex-wrap:wrap; gap:9px; margin:6px 0 16px; }
.vf-chip{
  display:flex; flex-direction:column; gap:1px; padding:9px 15px; border-radius:13px;
  background:var(--card); border:1px solid var(--line); min-width:92px;
}
.vf-chip em{ font-style:normal; font-size:.66rem; text-transform:uppercase; letter-spacing:.1em; color:var(--muted); }
.vf-chip b{ font-family:'Space Grotesk',sans-serif; font-size:1.15rem; color:#fff; }

/* confidence + badges */
.vf-req{ font-family:'Space Grotesk',sans-serif; font-size:1.15rem; font-weight:600; color:#fff; margin:8px 0 2px; }
.vf-req span{ color:var(--cyan); }
.vf-conf-top{ display:flex; justify-content:space-between; font-size:.74rem; color:var(--muted); margin-bottom:6px; letter-spacing:.04em; }
.vf-conf-top b{ font-family:'Space Grotesk',sans-serif; color:#fff; font-size:.95rem; }
.vf-bar{ height:11px; border-radius:99px; background:rgba(255,255,255,.07); overflow:hidden; box-shadow:inset 0 0 0 1px var(--line); }
.vf-bar>span{ display:block; height:100%; border-radius:99px; background:var(--grad); box-shadow:0 0 16px rgba(255,45,149,.55); }
.vf-badges{ display:flex; flex-wrap:wrap; gap:9px; margin:14px 0 2px; }
.vf-badge{ font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:.76rem; padding:6px 14px; border-radius:999px; border:1px solid transparent; }
.vf-badge.pass{ background:rgba(34,211,238,.14); color:#67e8f9; border-color:rgba(34,211,238,.4); }
.vf-badge.low{ background:rgba(251,191,36,.14); color:#fcd34d; border-color:rgba(251,191,36,.4); }
.vf-badge.att{ background:rgba(168,85,247,.16); color:#d8b4fe; border-color:rgba(168,85,247,.4); }
.vf-advisory{ margin-top:14px; font-size:.9rem; color:#fcd34d; background:rgba(251,191,36,.1);
  border:1px solid rgba(251,191,36,.3); border-left:4px solid #fbbf24; border-radius:12px; padding:11px 14px; }

.vf-sechead{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.2rem; color:#fff;
  margin:26px 0 12px; display:flex; align-items:center; gap:10px; }
.vf-sechead::after{ content:""; flex:1; height:1px; background:linear-gradient(90deg,var(--line),transparent); }

/* song cards */
.vf-song{
  position:relative; display:flex; gap:16px; align-items:stretch;
  background:var(--card); border:1px solid var(--line); border-radius:16px; padding:15px 18px 15px 22px;
  margin-bottom:11px; overflow:hidden;
}
.vf-song::before{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--grad); }
.vf-rank{ align-self:center; font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.8rem; width:1.1em; text-align:center; flex:none;
  background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
.vf-main{ flex:1; min-width:0; display:flex; flex-direction:column; gap:8px; }
.vf-row{ display:flex; align-items:center; justify-content:space-between; gap:12px; }
.vf-names{ min-width:0; }
.vf-title2{ font-weight:600; color:#fff; font-size:1.05rem; }
.vf-artist{ color:var(--muted); font-size:.86rem; }
.vf-score{ flex:none; font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.35rem;
  color:#fff; padding:5px 14px; border-radius:11px; background:rgba(168,85,247,.2); border:1px solid var(--line); }
.vf-reasons{ display:flex; flex-wrap:wrap; gap:6px; }
.vf-rchip{ font-size:.72rem; padding:3px 9px; border-radius:7px; background:rgba(34,211,238,.1); color:#8ee7f7; border:1px solid rgba(34,211,238,.25); white-space:nowrap; }

/* source pills + library panel */
.vf-src{ font-family:'Space Grotesk',sans-serif; font-size:.6rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em;
  padding:2px 8px; border-radius:999px; margin-left:9px; white-space:nowrap; }
.vf-src.lib{ background:rgba(255,45,149,.16); color:#ff8ac4; border:1px solid rgba(255,45,149,.4); }
.vf-src.sug{ background:rgba(168,85,247,.14); color:#c4b5fd; border:1px solid rgba(168,85,247,.35); }
.vf-lib{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px 18px; margin:4px 0 2px; }
.vf-libhead{ font-family:'Space Grotesk',sans-serif; font-weight:700; color:#fff; font-size:1.05rem; margin-bottom:11px; display:flex; align-items:center; gap:8px; }
.vf-gbreak{ display:flex; flex-wrap:wrap; gap:7px; margin-bottom:14px; }
.vf-gchip{ font-size:.74rem; padding:4px 12px; border-radius:999px; background:rgba(34,211,238,.1); border:1px solid rgba(34,211,238,.25); color:#8ee7f7; }
.vf-gchip b{ color:#fff; font-family:'Space Grotesk',sans-serif; }
.vf-track{ display:flex; justify-content:space-between; gap:12px; padding:8px 0; border-top:1px solid var(--line); font-size:.88rem; }
.vf-track .tname{ color:#fff; min-width:0; overflow:hidden; text-overflow:ellipsis; }
.vf-track .tname span{ color:var(--muted); }
.vf-track .tplays{ color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; }
.vf-more{ color:var(--muted); font-size:.8rem; margin-top:9px; }

/* expander (trace) */
[data-testid="stExpander"]{ border:1px solid var(--line)!important; border-radius:12px!important; background:var(--card)!important; }
[data-testid="stExpander"] summary{ color:var(--muted)!important; font-family:'Space Grotesk',sans-serif; font-weight:600; }
[data-testid="stExpander"] code{ color:#c4b5fd; background:rgba(124,58,237,.18); }

/* file uploader */
[data-testid="stFileUploaderDropzone"]{ background:rgba(255,255,255,.03)!important; border:1.5px dashed var(--line)!important; border-radius:14px!important; }
</style>
"""


@st.cache_resource
def get_agent() -> RecommenderAgent:
    """Load the agent (and its catalog) once per server session."""
    return RecommenderAgent()


def render_result(result) -> None:
    """Render one AgentResult as styled HTML (same data the CLI prints)."""
    p = result.profile
    req = html.escape(result.query or "(empty request)")
    conf_pct = int(round(min(1.0, max(0.0, result.confidence)) * 100))

    chips = "".join(
        f'<span class="vf-chip"><em>{name}</em><b>{html.escape(str(val))}</b></span>'
        for name, val in [
            ("genre", p.favorite_genre or "—"),
            ("mood", p.favorite_mood or "—"),
            ("energy", p.target_energy),
            ("acoustic", "yes" if p.likes_acoustic else "no"),
        ]
    )
    status = ('<span class="vf-badge pass">✓ passed self-check</span>' if result.passed
              else '<span class="vf-badge low">⚠ low confidence</span>')
    badges = status + f'<span class="vf-badge att">{result.attempts} attempt{"s" if result.attempts > 1 else ""}</span>'
    advisory = f'<div class="vf-advisory">{html.escape(result.advisory)}</div>' if result.advisory else ""

    st.markdown(
        f'<div class="vf-req">Request: <span>“{req}”</span></div>'
        f'<div class="vf-profile">{chips}</div>'
        f'<div class="vf-conf-top"><span>CONFIDENCE</span><b>{result.confidence:.2f}</b></div>'
        f'<div class="vf-bar"><span style="width:{conf_pct}%"></span></div>'
        f'<div class="vf-badges">{badges}</div>{advisory}',
        unsafe_allow_html=True,
    )

    is_library = result.library_tracks is not None

    # "From your library" panel (library mode only).
    if is_library:
        gb = "".join(
            f'<span class="vf-gchip">{html.escape(g)} · <b>{plays}</b></span>'
            for g, plays in (result.genre_breakdown or [])
        )
        tracks = sorted(result.library_tracks, key=lambda t: t.get("play_count", 0), reverse=True)
        shown = tracks[:15]
        rows = "".join(
            f'<div class="vf-track"><div class="tname">{html.escape(t["title"])} '
            f'<span>· {html.escape(t["artist"])} · {html.escape(t["genre"] or "—")}</span></div>'
            f'<div class="tplays">{t.get("play_count", 0)} plays</div></div>'
            for t in shown
        )
        more = (f'<div class="vf-more">+ {len(tracks) - len(shown)} more tracks</div>'
                if len(tracks) > len(shown) else "")
        st.markdown(
            f'<div class="vf-lib"><div class="vf-libhead">🎧 From your library '
            f'({len(result.library_tracks)} tracks)</div>'
            f'<div class="vf-gbreak">{gb}</div>{rows}{more}</div>',
            unsafe_allow_html=True,
        )

    cards = ['<div class="vf-sechead">Recommendations</div>']
    for rank, (song, score, explanation) in enumerate(result.recommendations, start=1):
        reasons = "".join(
            f'<span class="vf-rchip">{html.escape(r.strip())}</span>'
            for r in explanation.split(";") if r.strip()
        )
        if is_library:
            pill = ('<span class="vf-src lib">🎧 your library</span>'
                    if song.get("source") == "library"
                    else '<span class="vf-src sug">suggested</span>')
        else:
            pill = ""
        cards.append(
            f'<div class="vf-song"><div class="vf-rank">{rank}</div>'
            f'<div class="vf-main">'
            f'<div class="vf-row">'
            f'<div class="vf-names"><div class="vf-title2">{html.escape(song["title"])}{pill}</div>'
            f'<div class="vf-artist">{html.escape(song["artist"])}</div></div>'
            f'<div class="vf-score">{score:.2f}</div></div>'
            f'<div class="vf-reasons">{reasons}</div></div></div>'
        )
    st.markdown("".join(cards), unsafe_allow_html=True)

    with st.expander(f"⚙ Agent trace ({len(result.trace)} steps)"):
        for step in result.trace:
            st.markdown(f"- `{step}`")


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<p class="vf-eyebrow">plan › act › check › revise</p>'
        '<h1 class="vf-title">VibeFinder Agent</h1>'
        '<p class="vf-sub">Tell it what you\'re in the mood for. The agent plans a taste '
        'profile, recommends songs, scores its own confidence, and quietly retries when it '
        'isn\'t sure — the same engine as <code>python -m src.main</code>.</p>',
        unsafe_allow_html=True,
    )

    agent = get_agent()
    tab_text, tab_library = st.tabs(["💬  Type a request", "🎧  Apple Music library"])

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
        go = st.button("✦ Recommend", type="primary")
        if go or query:
            render_result(agent.run(query))

    # --- Apple Music tab ---
    with tab_library:
        st.write(
            "Upload a library exported from the macOS Music app "
            "(**File → Library → Export Library…**), or use the bundled sample. "
            "No API key or Apple Developer account needed."
        )
        uploaded = st.file_uploader("Library.xml", type=["xml"])
        use_sample = st.button("🎧 Use bundled sample library")

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
