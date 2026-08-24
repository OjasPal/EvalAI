import os
from typing import Any, cast

import requests
import streamlit as st


st.set_page_config(
    page_title="EvalAI — Human Preference AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


DEFAULT_API = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)


def inject_css(dark_mode: bool = False) -> None:

    st.markdown(
        """
        <style>

        @import url(
            'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap'
        );

        :root {
            --brand-teal: #4f46e5;
            --brand-orange: #ea580c;
            --surface: #f1f5f9;
            --text: #1e293b;
            --muted: #64748b;
            --heading: #0f172a;
        }

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
            color: var(--text);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
        }

        p, li {
            line-height: 1.62;
            font-size: 1rem;
            letter-spacing: .002em;
        }

        h1, h2, h3, h4 {
            color: var(--heading);
            letter-spacing: -0.015em;
        }

        h2 {
            font-size: 1.55rem;
            font-weight: 780;
            margin-top: .15rem;
        }

        h3 {
            font-size: 1.12rem;
            font-weight: 740;
            margin-top: .35rem;
        }

        [data-testid="stCaptionContainer"] {
            color: var(--muted);
            font-size: .93rem;
            line-height: 1.5;
        }

        #MainMenu,
        header,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stDeployButton"] {
            visibility: hidden;
            height: 0;
            position: fixed;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        .hero {
            padding: 1.6rem 1.8rem;
            border-radius: 18px;
            border: 1px solid rgba(79, 70, 229, .35);
            margin-bottom: 1.2rem;
            background: linear-gradient(
                135deg,
                #4f46e5,
                #7c3aed
            );
            box-shadow:
                0 12px 34px rgba(79, 70, 229, .28);
        }

        .hero h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #f5f8f8;
            text-shadow:
                0 2px 10px rgba(0,0,0,.18);
        }

        .hero p {
            margin: .45rem 0 0;
            color: rgba(241, 246, 247, .92);
            font-size: 1.02rem;
        }

        .workflow-note {
            padding: .78rem 1rem;
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 10px;
            margin: .4rem 0 1rem;
            background: rgba(128,128,128,.06);
            font-size: .93rem;
            line-height: 1.52;
        }

        .response-heading {
            padding: .68rem .88rem;
            border-radius: 8px;
            margin-bottom: .35rem;
            font-weight: 700;
            letter-spacing: .01em;
            background: rgba(79,70,229,.1);
            color: #4338ca;
        }

        .response-heading.a {
            border-left: 4px solid var(--brand-teal);
        }

        .response-heading.b {
            border-left: 4px solid var(--brand-orange);
            background: rgba(234,88,12,.1);
            color: #c2410c;
        }

        .winner-card {
            padding: 1.35rem;
            border-radius: 10px;
            border: 1px solid rgba(234,88,12,.3);
            margin: .8rem 0 1rem;
            background: linear-gradient(
                110deg,
                rgba(234,88,12,.14),
                rgba(79,70,229,.1)
            );
        }

        .winner-card h2 {
            margin: 0;
            font-size: 1.38rem;
            font-weight: 800;
            color: #1e293b;
        }

        .small-muted {
            opacity: .68;
            font-size: .92rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: .5rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(148,163,184,.35);
            border-radius: 10px;
            padding: .68rem;
            background: rgba(79, 70, 229, .06);
        }

        [data-testid="stMetricLabel"] {
            font-size: .83rem;
            color: var(--muted);
            font-weight: 600;
            letter-spacing: .02em;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.22rem;
            font-weight: 760;
            color: #0f172a;
        }

        div.stButton > button {
            min-height: 2.8rem;
            border-radius: 10px;
            font-weight: 700;
            letter-spacing: .01em;
            font-size: .97rem;
        }

        div.stButton > button:not(:disabled) {
            cursor: pointer !important;
        }

        div.stButton > button:disabled {
            cursor: not-allowed !important;
        }

        [data-testid="stTabs"] {
            margin-top: .2rem;
            margin-bottom: .85rem;
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: .9rem;
            padding: .35rem;
            border: 1px solid rgba(148, 163, 184, .3);
            border-radius: 14px;
            background: #f1f5f9;
            overflow: hidden;
        }

        [data-testid="stTabs"] button {
            flex: 1 1 0;
            font-weight: 730;
            font-size: .95rem;
            letter-spacing: .01em;
            color: #475569;
            border-radius: 10px;
            border: 1px solid transparent;
            padding: .55rem .88rem;
            background: transparent;
            transition: all .2s ease;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #ffffff;
            background: linear-gradient(
                135deg,
                #4f46e5,
                #7c3aed
            );
            border-color: transparent;
            box-shadow:
                0 4px 12px rgba(79, 70, 229, .3);
            font-weight: 780;
        }

        [data-testid="stTabs"] button:hover {
            color: #4338ca;
            background: rgba(79, 70, 229, .1);
            border-color: rgba(79, 70, 229, .2);
        }

        .stTextArea textarea {
            font-size: .98rem;
            line-height: 1.58;
            color: #1e293b !important;
            -webkit-text-fill-color: #1e293b;
            background: #ffffff !important;
            caret-color: #4f46e5;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
        }

        .stTextArea textarea::placeholder {
            color: #94a3b8 !important;
            -webkit-text-fill-color: #94a3b8;
            opacity: 1;
        }

        .stTextArea textarea:focus {
            border-color: #4f46e5;
            box-shadow:
                0 0 0 2px rgba(79, 70, 229, .18);
        }

        .stCodeBlock {
            border-radius: 10px;
            overflow: hidden;
        }

        .stRadio label {
            font-weight: 600;
            color: #1e293b;
        }

        .about-card {
            border: 1px solid rgba(148,163,184,.3);
            border-radius: 14px;
            padding: 1rem;
            background: rgba(79, 70, 229, .06);
            min-height: 120px;
        }

        .about-card h4 {
            margin-top: 0;
            margin-bottom: .5rem;
        }

        .about-card p {
            margin-bottom: 0;
            color: var(--muted);
        }

        .bias-good {
            border-left: 4px solid #16a34a;
            padding: .7rem .9rem;
            border-radius: 8px;
            background: rgba(22,163,74,.08);
        }

        .bias-warning {
            border-left: 4px solid #ea580c;
            padding: .7rem .9rem;
            border-radius: 8px;
            background: rgba(234,88,12,.08);
        }

        .bias-danger {
            border-left: 4px solid #dc2626;
            padding: .7rem .9rem;
            border-radius: 8px;
            background: rgba(220,38,38,.08);
        }

        .model-status {
            padding: .8rem 1rem;
            border-radius: 10px;
            border: 1px solid rgba(79,70,229,.2);
            background: rgba(79,70,229,.06);
            margin: .5rem 0 1rem;
            color: #1e293b;
        }

        /* -------------------------------------------
           HUMAN FEEDBACK / RETRAINING UI
           ------------------------------------------- */

        .feedback-learning-card {
            padding: 1rem 1.1rem;
            border-radius: 12px;
            border: 1px solid rgba(79,70,229,.22);
            background: rgba(79,70,229,.055);
            margin: .5rem 0 1rem;
        }

        .feedback-learning-card strong {
            color: #1e293b;
        }

        .feedback-learning-card span {
            color: #64748b;
        }

        .feedback-stat-card {
            padding: .9rem 1rem;
            border-radius: 12px;
            border: 1px solid rgba(148,163,184,.3);
            background: rgba(79,70,229,.05);
        }

        .feedback-stat-label {
            font-size: .78rem;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: .03em;
        }

        .feedback-stat-value {
            margin-top: .25rem;
            font-size: 1.1rem;
            font-weight: 750;
            color: #1e293b;
        }
        
.confusion-matrix {
    border: 1px solid rgba(148,163,184,.3);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    background: rgba(79, 70, 229, .06);
    overflow-x: auto;
}
.confusion-matrix table { width: 100%; border-collapse: collapse; font-size: .95rem; }
.confusion-matrix th, .confusion-matrix td { padding: .45rem .75rem; text-align: right; color: var(--text); }
.confusion-matrix th:first-child, .confusion-matrix td:first-child { text-align: left; color: var(--muted); font-weight: 600; }
.confusion-matrix th { color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: .78rem; border-bottom: 1px solid rgba(148,163,184,.25); }

        /* Number input */
        [data-testid="stNumberInput"] input {
            border-radius: 10px !important;
            border: 1px solid #cbd5e1 !important;
            color: #1e293b !important;
            background: #ffffff !important;
            -webkit-text-fill-color: #1e293b !important;
        }

        [data-testid="stNumberInput"] input:focus {
            border-color: #4f46e5 !important;
            box-shadow:
                0 0 0 2px rgba(79,70,229,.18) !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    if dark_mode:

        st.markdown(
            """
            <style>

            :root {
                --surface: #1e293b;
                --text: #f1f5f9;
                --muted: #94a3b8;
                --heading: #f8fafc;
            }

            .stApp {
                background: #0f172a;
            }

            [data-testid="stCaptionContainer"],
            .about-card p,
            .small-muted {
                color: #94a3b8;
            }

            .workflow-note,
            .about-card,
            div[data-testid="stMetric"] {
                background: rgba(30, 41, 59, .8);
                border-color: rgba(148, 163, 184, .25);
            }

            .workflow-note {
                color: #f1f5f9 !important;
            }

            .winner-card h2,
            [data-testid="stMetricValue"] {
                color: #f8fafc;
            }

            [data-testid="stMetricLabel"] {
                color: #94a3b8;
            }

            .stTextArea textarea {
                background: #1e293b !important;
                color: #f1f5f9 !important;
                -webkit-text-fill-color: #f1f5f9;
                border: 1px solid #334155;
            }

            [data-testid="stTabs"] [role="tablist"] {
                background: #1e293b;
                border-color: rgba(148, 163, 184, .25);
            }

            [data-testid="stTabs"] button {
                color: #cbd5e1;
                background: transparent;
            }

            [data-testid="stTabs"] button[aria-selected="true"] {
                color: #ffffff;
                background: linear-gradient(
                    135deg,
                    #6366f1,
                    #8b5cf6
                );
            }

            [data-testid="stTabs"] button:hover {
                color: #f8fafc;
            }

            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] span,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] strong,
            [data-testid="stWidgetLabel"] p,
            [data-testid="stWidgetLabel"] label,
            [data-testid="stText"],
            .stRadio label,
            .stRadio label p,
            .stRadio [data-testid="stMarkdownContainer"] {
                color: #f1f5f9 !important;
            }

            div.stButton > button {
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
                border: 1px solid #334155 !important;
            }

            div.stButton > button:hover {
                background-color: #334155 !important;
                border-color: #6366f1 !important;
                color: #ffffff !important;
            }

            div.stButton > button[kind="primary"] {
                background: linear-gradient(
                    135deg,
                    #6366f1,
                    #8b5cf6
                ) !important;
                color: #ffffff !important;
                border: none !important;
            }

            div.stButton > button:disabled {
                background-color: #1e293b !important;
                color: #64748b !important;
                border: 1px solid #334155 !important;
            }

            [data-testid="stExpander"] {
                background: rgba(30, 41, 59, .6) !important;
                border: 1px solid rgba(148, 163, 184, .25) !important;
                border-radius: 10px;
            }

            [data-testid="stExpander"] summary,
            [data-testid="stExpander"] summary p {
                color: #f1f5f9 !important;
            }

            [data-testid="stAlert"] {
                background: #1e293b !important;
                border: 1px solid #334155 !important;
                border-radius: 10px !important;
            }

            [data-testid="stAlert"] p,
            [data-testid="stAlert"] span,
            [data-testid="stAlertContentInfo"],
            [data-testid="stAlertContentWarning"],
            [data-testid="stAlertContentError"],
            [data-testid="stAlertContentSuccess"] {
                color: #f1f5f9 !important;
            }

            hr {
                border-color: rgba(148, 163, 184, .25) !important;
            }

            /* -------------------------------------------
               DARK MODE — HUMAN FEEDBACK / RETRAINING
               ------------------------------------------- */

            .model-status {
                background: #17213a !important;
                border: 1px solid #33446b !important;
                color: #cbd5e1 !important;
            }

            .model-status b {
                color: #f8fafc !important;
            }

            .feedback-learning-card {
                background: #17213a !important;
                border: 1px solid #33446b !important;
                color: #cbd5e1 !important;
            }

            .feedback-learning-card strong {
                color: #f8fafc !important;
            }

            .feedback-learning-card span {
                color: #cbd5e1 !important;
            }

            .feedback-stat-card {
                background: #1e293b !important;
                border: 1px solid #334155 !important;
                color: #f8fafc !important;
            }
            
.confusion-matrix { background: rgba(30, 41, 59, .8) !important; border-color: rgba(148, 163, 184, .25) !important; }
.confusion-matrix th, .confusion-matrix td { color: #f1f5f9 !important; }
.confusion-matrix th:first-child, .confusion-matrix td:first-child { color: #94a3b8 !important; }

            .feedback-stat-label {
                color: #94a3b8 !important;
            }

            .feedback-stat-value {
                color: #f8fafc !important;
            }

            /* Dark number input */
            [data-testid="stNumberInput"] input {
                background: #1e293b !important;
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                border: 1px solid #334155 !important;
            }

            [data-testid="stNumberInput"] input:focus {
                border-color: #6366f1 !important;
                box-shadow:
                    0 0 0 2px rgba(99,102,241,.22) !important;
            }

            [data-testid="stNumberInput"] button {
                background: #1e293b !important;
                color: #cbd5e1 !important;
                border-color: #334155 !important;
            }

            [data-testid="stNumberInput"] button:hover {
                background: #334155 !important;
                color: #ffffff !important;
            }

            </style>
            """,
            unsafe_allow_html=True,
        )


def api_url(
    base: str,
    path: str,
) -> str:

    return base.rstrip("/") + path


def post_json(
    base: str,
    path: str,
    payload: dict[str, Any],
    timeout: int = 180,
) -> tuple[
    dict[str, Any] | None,
    str | None,
]:

    try:

        response = requests.post(
            api_url(base, path),
            json=payload,
            timeout=timeout,
        )

    except requests.RequestException as exc:

        return (
            None,
            f"Could not connect to FastAPI: {exc}",
        )

    if not response.ok:

        try:
            detail = response.json().get(
                "detail",
                response.text,
            )

        except ValueError:
            detail = response.text

        return (
            None,
            "Backend returned HTTP "
            f"{response.status_code}: {detail}",
        )

    try:

        data = response.json()

        if not isinstance(data, dict):

            return (
                None,
                "Backend returned a JSON response "
                "with an invalid shape.",
            )

        return data, None

    except ValueError:

        return (
            None,
            "Backend returned an invalid JSON response.",
        )


@st.cache_data(ttl=5, show_spinner=False)
def get_health(
    base: str,
) -> tuple[
    dict[str, Any] | None,
    str | None,
]:

    try:

        response = requests.get(
            api_url(base, "/health"),
            timeout=5,
        )

    except requests.RequestException as exc:

        return None, str(exc)

    if not response.ok:

        return (
            None,
            f"HTTP {response.status_code}",
        )

    try:

        data = response.json()

        if not isinstance(data, dict):

            return (
                None,
                "Backend returned an invalid health response.",
            )

        return data, None

    except ValueError:

        return (
            None,
            "Invalid JSON response.",
        )


def score_bar(
    label: str,
    score: float,
) -> None:

    st.markdown(
        f"**{label} — {score:.1%}**"
    )

    st.progress(
        max(
            0.0,
            min(1.0, score),
        )
    )


def prediction_values(
    data: Any,
) -> tuple[
    str,
    float,
    float,
    float,
] | None:

    if not isinstance(data, dict):
        return None

    winner = data.get("winner")

    if winner not in {"A", "B"}:
        return None

    try:

        confidence = float(
            data["confidence"]
        )

        score_a = float(
            data["score_a"]
        )

        score_b = float(
            data["score_b"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return None

    if not all(
        0.0 <= score <= 1.0
        for score in (
            score_a,
            score_b,
            confidence,
        )
    ):
        return None

    return (
        winner,
        confidence,
        score_a,
        score_b,
    )


def backend_status_summary(
    health: dict[str, Any] | None,
    error: str | None,
) -> tuple[
    str,
    str,
    str,
]:

    if health is None:

        return (
            "offline",
            "Backend offline",
            error
            or "Could not reach the backend service.",
        )

    status = str(
        health.get(
            "status",
            "unknown",
        )
    ).lower()

    if status == "ok":

        return (
            "online",
            "Backend online",
            "API and model are ready.",
        )

    if status == "degraded":

        return (
            "degraded",
            "Backend degraded",
            str(
                health.get(
                    "error",
                    "Model is unavailable.",
                )
            ),
        )

    return (
        "starting",
        "Backend starting",
        "Service is up but still initializing.",
    )


def bias_severity_class(
    severity: str,
) -> str:

    severity = severity.lower()

    if severity == "low":
        return "bias-good"

    if severity == "moderate":
        return "bias-warning"

    return "bias-danger"


def render_bias_status(
    severity: str,
    title: str,
    description: str,
) -> None:

    css_class = bias_severity_class(
        severity
    )

    st.markdown(
        f"""
        <div class="{css_class}">
            <b>{title}: {severity}</b><br>
            <span>{description}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compare_page(
    base: str,
    backend_available: bool,
) -> None:

    st.markdown(
        "## Compare two LLM responses"
    )

    st.caption(
        "Give the same user prompt and two competing responses. "
        "EvalAI predicts which response a human is more likely to prefer."
    )

    st.markdown(
        """
        <div class="workflow-note">
            <b>Workflow:</b> enter a prompt, generate or paste two answers,
            then compare them with the trained preference model.
        </div>
        """,
        unsafe_allow_html=True,
    )

    prompt = st.text_area(
        "User prompt",
        height=120,
        placeholder=(
            "Example: Explain quantum computing in simple terms."
        ),
    )

    generated_prompt = st.session_state.get(
        "generated_prompt"
    )

    if (
        generated_prompt
        and generated_prompt != prompt
    ):

        st.info(
            "The prompt changed. Generate new responses "
            "before comparing."
        )

    generate = st.button(
        "Generate two responses",
        type="secondary",
        use_container_width=True,
        disabled=not backend_available,
    )

    if not backend_available:

        st.warning(
            "Backend is not ready yet. "
            "Open the About tab to check live backend status."
        )

    if generate:

        if not prompt.strip():

            st.warning(
                "Enter a user prompt before generating responses."
            )

        else:

            with st.spinner(
                "Generating two responses with Ollama..."
            ):

                generated, error = post_json(
                    base,
                    "/generate",
                    {
                        "prompt": prompt,
                    },
                )

            if error:

                st.error(error)

            elif not isinstance(
                generated,
                dict,
            ):

                st.error(
                    "Backend returned an invalid generation response."
                )

            elif not isinstance(
                generated.get("response_a"),
                str,
            ) or not isinstance(
                generated.get("response_b"),
                str,
            ):

                st.error(
                    "Backend generation response is missing "
                    "Response A or Response B."
                )

            else:

                st.session_state[
                    "generated_response_a"
                ] = generated["response_a"]

                st.session_state[
                    "generated_response_b"
                ] = generated["response_b"]

                st.session_state[
                    "generated_prompt"
                ] = prompt.strip()

                st.session_state.pop(
                    "last_prediction",
                    None,
                )

                st.session_state.pop(
                    "last_input",
                    None,
                )

                st.rerun()

    response_a_default = str(
        st.session_state.get(
            "generated_response_a"
        )
        or ""
    )

    response_b_default = str(
        st.session_state.get(
            "generated_response_b"
        )
        or ""
    )

    col_a, col_b = st.columns(
        2,
        gap="large",
    )

    with col_a:

        st.markdown(
            '<div class="response-heading a">'
            "Response A"
            "</div>",
            unsafe_allow_html=True,
        )

        response_a = st.text_area(
            "Response A text",
            height=260,
            placeholder=(
                "Paste the first LLM response..."
            ),
            value=response_a_default,
            label_visibility="collapsed",
        )

    with col_b:

        st.markdown(
            '<div class="response-heading b">'
            "Response B"
            "</div>",
            unsafe_allow_html=True,
        )

        response_b = st.text_area(
            "Response B text",
            height=260,
            placeholder=(
                "Paste the second LLM response..."
            ),
            value=response_b_default,
            label_visibility="collapsed",
        )

    compare = st.button(
        "⚖️ Compare Responses",
        type="primary",
        use_container_width=True,
        disabled=not backend_available,
    )

    if compare:

        if not prompt.strip() or not response_a.strip() or not response_b.strip():

            st.warning(
                "Please provide the prompt, Response A, and Response B."
            )

            return

        if (
            generated_prompt
            and generated_prompt != prompt.strip()
        ):

            st.warning(
                "Generate new responses for the changed prompt "
                "before comparing."
            )

            return

        with st.spinner(
            "Running preference model..."
        ):

            data, error = post_json(
                base,
                "/predict",
                {
                    "prompt": prompt,
                    "response_a": response_a,
                    "response_b": response_b,
                },
            )

        if error:

            st.error(error)

            return

        st.session_state[
            "last_prediction"
        ] = data

        st.session_state[
            "last_input"
        ] = {
            "prompt": prompt,
            "response_a": response_a,
            "response_b": response_b,
        }

    data = st.session_state.get(
        "last_prediction"
    )

    if not data:
        return

    st.divider()

    st.markdown(
        "## AI preference prediction"
    )

    values = prediction_values(data)

    if values is None:

        st.error(
            "FastAPI returned an invalid prediction response."
        )

        return

    (
        winner,
        confidence,
        score_a,
        score_b,
    ) = values

    headline = (
        "Response A is predicted to be preferred"
        if winner == "A"
        else
        "Response B is predicted to be preferred"
    )

    st.markdown(
        f"""
        <div class="winner-card">
            <h2>🏆 {headline}</h2>
            <div class="small-muted">
                Model confidence: {confidence:.1%}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_a, metric_b, metric_c = st.columns(3)

    metric_a.metric(
        "Response A",
        f"{score_a:.1%}",
    )

    metric_b.metric(
        "Response B",
        f"{score_b:.1%}",
    )

    metric_c.metric(
        "Confidence",
        f"{confidence:.1%}",
    )

    st.markdown(
        "### Preference scores"
    )

    score_bar(
        "Response A",
        score_a,
    )

    score_bar(
        "Response B",
        score_b,
    )

    if data.get("demo_mode"):

        st.info(
            "Demo mode is active. These scores are placeholders "
            "for integration testing, not real model predictions."
        )

    st.caption(
        f"Model: {data.get('model', 'RoBERTa')}"
    )


def feedback_page(
    base: str,
    compact: bool = False,
) -> None:

    if not compact:
        st.markdown(
            "## Human feedback"
        )

        st.caption(
            "Evaluate both responses across multiple human-preference dimensions. "
            "Your feedback is stored for preference-model learning."
        )

    prediction = st.session_state.get(
        "last_prediction"
    )

    inputs = st.session_state.get(
        "last_input"
    )

    if not prediction or not inputs:

        st.info(
            "Run a comparison first, then return here "
            "to record your preference."
        )

        return

    st.markdown(
        """
        <div class="workflow-note">
            <b>Review both responses:</b> choose your overall preference,
            then rate each response from 1 (poor) to 5 (excellent).
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 1. Overall preference"
    )

    choice = st.radio(
        "Human preference",
        ["A", "B", "Tie"],
        horizontal=True,
        key=(
            "human_preference_compact"
            if compact
            else "human_preference_page"
        ),
        label_visibility="collapsed",
    )

    st.markdown(
        "### 2. Multi-dimensional evaluation"
    )

    st.caption(
        "Rate both responses independently. These ratings strengthen the "
        "training signal without changing the existing RoBERTa prediction API."
    )

    dimensions = [
        ("Helpfulness", "helpfulness"),
        ("Correctness", "correctness"),
        ("Relevance", "relevance"),
        ("Clarity", "clarity"),
        ("Safety", "safety"),
    ]

    ratings: dict[str, int] = {}

    for label, key in dimensions:

        col_a, col_b = st.columns(
            2,
            gap="large",
        )

        with col_a:

            ratings[f"{key}_a"] = st.slider(
                f"Response A — {label}",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                key=(
                    f"{key}_a_compact"
                    if compact
                    else f"{key}_a_page"
                ),
            )

        with col_b:

            ratings[f"{key}_b"] = st.slider(
                f"Response B — {label}",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                key=(
                    f"{key}_b_compact"
                    if compact
                    else f"{key}_b_page"
                ),
            )

    if st.button(
        "Submit human evaluation",
        type="secondary",
        key=(
            "submit_feedback_compact"
            if compact
            else "submit_feedback_page"
        ),
    ):

        payload = {
            "request_id": prediction.get(
                "request_id"
            ),
            **inputs,
            "human_preference": choice,
            **ratings,
        }

        with st.spinner(
            "Saving multi-dimensional human feedback..."
        ):

            data, error = post_json(
                base,
                "/feedback",
                payload,
                timeout=20,
            )

        if error:

            st.error(error)

        else:

            st.success(
                "Feedback saved: overall preference + "
                "five evaluation dimensions."
            )

            st.session_state[
                "feedback_last_saved"
            ] = True


def retraining_panel(
    base: str,
    panel_id: str,
) -> None:

    st.markdown(
        "### Human-feedback learning"
    )

    st.caption(
        "Use collected A/B feedback to fine-tune the current "
        "RoBERTa preference model. The backend evaluates the "
        "candidate before activating it."
    )

    if panel_id == "evaluation":
        st.markdown(
            """
            <div class="model-status">
                Your feedback is saved and used to improve the AI.
                The current AI stays unchanged until the improved version
                is tested and works better.
            </div>
            """,
            unsafe_allow_html=True,
        )

    min_feedback = st.number_input(
        "Minimum A/B feedback examples",
        min_value=2,
        max_value=100000,
        value=20,
        step=1,
        help=(
            "Tie feedback is stored but is not used by the "
            "current binary preference-training pipeline."
        ),
        key=f"retrain_min_feedback_{panel_id}",
    )

    if st.button(
        "🔄 Retrain Preference Model",
        type="primary",
        use_container_width=True,
        key=f"retrain_model_button_{panel_id}",
    ):

        with st.spinner(
            "Training candidate model and validating it..."
        ):

            data, error = post_json(
                base,
                "/retrain",
                {
                    "min_feedback": int(
                        min_feedback
                    )
                },
                timeout=3600,
            )

        if error:

            st.error(error)

            return

        if not isinstance(
            data,
            dict,
        ):

            st.error(
                "Backend returned an invalid retraining response."
            )

            return

        status = str(
            data.get(
                "status",
                "unknown",
            )
        )

        message = str(
            data.get(
                "message",
                "",
            )
        )

        feedback_examples = data.get(
            "feedback_examples",
            "N/A",
        )

        model = data.get(
            "model",
            "N/A",
        )

        if status == "completed":

            st.success(
                "✅ New preference model activated."
            )

        elif status == "rejected":

            st.warning(
                "⚠️ Candidate rejected. "
                "Current model remains active."
            )

        elif status == "failed":

            st.error(
                "❌ Retraining failed. "
                "Current model remains active."
            )

        else:

            st.info(
                f"Retraining status: {status}"
            )

        st.write(
            message
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "Feedback examples",
            str(feedback_examples),
        )

        c2.metric(
            "Active model",
            str(model),
        )


def evaluation_page(
    base: str,
) -> None:

    st.markdown(
        "## Evaluation & bias analysis"
    )

    st.caption(
        "Run the trained RoBERTa preference model against the "
        "read-only held-out test split."
    )

    st.info(
        "A full run evaluates every pair in preprocess/test.csv "
        "twice: original order and swapped order. "
        "This provides quality, position-bias and verbosity-bias signals."
    )

    if st.button(
        "Start Held-Out Evaluation",
        type="primary",
    ):

        with st.spinner(
            "Evaluating the held-out split and running "
            "position/verbosity checks..."
        ):

            data, error = post_json(
                base,
                "/evaluation",
                {},
                timeout=3600,
            )

        if error:

            st.error(error)

        else:

            st.session_state[
                "evaluation_result"
            ] = data

    data = st.session_state.get(
        "evaluation_result"
    )

    if not isinstance(
        data,
        dict,
    ):

        st.warning(
            "No held-out evaluation has been run in this session."
        )

        retraining_panel(
            base,
            "evaluation",
        )

        return

    metrics_value = data.get(
        "metrics"
    )

    position_value = data.get(
        "position_bias"
    )

    verbosity_value = data.get(
        "verbosity_bias"
    )

    if not all(
        isinstance(section, dict)
        for section in (
            metrics_value,
            position_value,
            verbosity_value,
        )
    ):

        st.error(
            "FastAPI returned an invalid evaluation response."
        )

        return

    metrics = cast(
        dict[str, Any],
        metrics_value,
    )

    position = cast(
        dict[str, Any],
        position_value,
    )

    verbosity = cast(
        dict[str, Any],
        verbosity_value,
    )

    def percent(
        value: Any,
    ) -> str:

        try:

            return f"{float(value):.1%}"

        except (
            TypeError,
            ValueError,
        ):

            return "Not available"

    def signed_percent(
        value: Any,
    ) -> str:

        try:

            return f"{float(value):+.1%}"

        except (
            TypeError,
            ValueError,
        ):

            return "Not available"

    st.success(
        f"Evaluated "
        f"{data.get('examples_evaluated', 'the available')} "
        "held-out pairs with the RoBERTa model."
    )

    st.markdown(
        "### Benchmark metrics"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Accuracy",
        percent(
            metrics.get("accuracy")
        ),
    )

    c2.metric(
        "Precision",
        percent(
            metrics.get("precision")
        ),
    )

    c3.metric(
        "Recall",
        percent(
            metrics.get("recall")
        ),
    )

    c4.metric(
        "F1-score",
        percent(
            metrics.get("f1")
        ),
    )

    c5.metric(
        "ROC-AUC",
        percent(
            metrics.get("roc_auc")
        ),
    )

    if (
        metrics.get("roc_auc") is None
        and metrics.get("roc_auc_reason")
    ):

        st.caption(
            str(
                metrics[
                    "roc_auc_reason"
                ]
            )
        )

    matrix = metrics.get(
        "confusion_matrix"
    )

    if (
        isinstance(matrix, list)
        and len(matrix) == 2
        and all(
            isinstance(row, list)
            and len(row) == 2
            for row in matrix
        )
    ):
        st.markdown(
            "#### Confusion matrix"
        )

        st.markdown(
            f"""
            <div class="confusion-matrix">
                <table>
                    <tr><th></th><th>Predicted A</th><th>Predicted B</th></tr>
                    <tr><td>Actual A</td><td>{matrix[0][0]}</td><td>{matrix[0][1]}</td></tr>
                    <tr><td>Actual B</td><td>{matrix[1][0]}</td><td>{matrix[1][1]}</td></tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    class_metrics = metrics.get(
        "class_metrics"
    )

    if isinstance(
        class_metrics,
        dict,
    ):

        st.markdown(
            "#### Per-class metrics"
        )

        class_a, class_b = st.columns(2)

        for column, label in (
            (class_a, "A"),
            (class_b, "B"),
        ):

            values = class_metrics.get(
                label
            )

            if isinstance(
                values,
                dict,
            ):

                with column:

                    st.caption(
                        f"Response {label} preferred "
                        f"(support: "
                        f"{values.get('support', 'not available')})"
                    )

                    st.write(
                        f"Precision "
                        f"{percent(values.get('precision'))} · "
                        f"Recall "
                        f"{percent(values.get('recall'))} · "
                        f"F1 "
                        f"{percent(values.get('f1'))}"
                    )

    st.caption(
        f"Source: "
        f"{data.get('dataset', 'preprocess/test.csv')}"
    )

    st.markdown(
        "### Position bias"
    )

    st.caption(
        "A position-neutral model should change its winner "
        "when the same responses swap positions."
    )

    b1, b2, b3 = st.columns(3)

    inconsistent_rate = position.get(
        "inconsistent_swap_rate"
    )

    combined_first_rate = position.get(
        "combined_first_position_win_rate"
    )

    neutrality = (
        1.0 - float(inconsistent_rate)
        if inconsistent_rate is not None
        else None
    )

    b1.metric(
        "Inconsistent swap rate",
        percent(
            inconsistent_rate
        ),
    )

    b2.metric(
        "Order neutrality",
        percent(
            neutrality
        ),
    )

    b3.metric(
        "First-position win rate",
        percent(
            combined_first_rate
        ),
    )

    if inconsistent_rate is not None:

        rate = float(
            inconsistent_rate
        )

        if rate <= 0.10:

            render_bias_status(
                "Low",
                "Position bias",
                "Predictions are largely consistent "
                "when response positions are swapped.",
            )

        elif rate <= 0.25:

            render_bias_status(
                "Moderate",
                "Position bias",
                "Some predictions depend on response order. "
                "Treat borderline comparisons cautiously.",
            )

        else:

            render_bias_status(
                "High",
                "Position bias",
                "A significant portion of comparisons "
                "changes unexpectedly after swapping positions.",
            )

    st.caption(
        f"{position.get('inconsistent_swaps', 'Not available')} "
        f"of {position.get('pairs_evaluated', 'Not available')} "
        "pairs did not flip to the corresponding response "
        "after A/B order was reversed."
    )

    st.caption(
        "The 50% first-position rate is the order-neutral reference."
    )

    st.markdown(
        "### Verbosity bias"
    )

    v1, v2, v3 = st.columns(3)

    longer_rate = verbosity.get(
        "longer_response_win_rate"
    )

    excess = verbosity.get(
        "longer_response_win_rate_excess_over_chance"
    )

    correlation = verbosity.get(
        "length_delta_prediction_correlation"
    )

    v1.metric(
        "Longer response win rate",
        percent(longer_rate),
        signed_percent(excess),
    )

    v2.metric(
        "Bias magnitude",
        percent(
            abs(float(excess))
            if excess is not None
            else None
        ),
    )

    if correlation is None:

        v3.metric(
            "Length correlation",
            "N/A",
        )

    else:

        v3.metric(
            "Length correlation",
            f"{float(correlation):+.3f}",
        )

    if excess is not None:

        magnitude = abs(
            float(excess)
        )

        if magnitude <= 0.05:

            render_bias_status(
                "Low",
                "Verbosity bias",
                "Response length has only a small "
                "preference imbalance.",
            )

        elif magnitude <= 0.15:

            render_bias_status(
                "Moderate",
                "Verbosity bias",
                "Longer answers receive a noticeable "
                "preference advantage/disadvantage.",
            )

        else:

            render_bias_status(
                "High",
                "Verbosity bias",
                "Response length has a strong association "
                "with model preference.",
            )

    st.caption(
        f"Longer response won "
        f"{verbosity.get('longer_response_wins', 'not available')} "
        f"of "
        f"{verbosity.get('pairs_with_different_lengths', 'not available')} "
        "pairs with different lengths."
    )

    if correlation is None:

        st.caption(
            str(
                verbosity.get(
                    "correlation_reason",
                    "Correlation not available.",
                )
            )
        )

    else:

        st.caption(
            "Length-delta/prediction correlation: "
            f"{float(correlation):+.3f}."
        )

    st.markdown(
        "### Bias-aware interpretation"
    )

    st.caption(
        "EvalAI uses swapped-order evaluation to reduce the risk "
        "of treating presentation position as genuine preference."
    )

    if (
        inconsistent_rate is not None
        and float(inconsistent_rate) <= 0.10
    ):

        st.success(
            "✓ The model shows strong order consistency. "
            "Position effects appear limited on this evaluation split."
        )

    elif (
        inconsistent_rate is not None
        and float(inconsistent_rate) <= 0.25
    ):

        st.warning(
            "⚠ Some order sensitivity is present. "
            "For close predictions, evaluate both response orderings."
        )

    else:

        st.error(
            "✕ Strong order sensitivity detected. "
            "Single-order predictions should be treated cautiously."
        )

    with st.expander(
        "How the bias analysis works"
    ):

        st.write(
            "The model is evaluated on the original test pair and "
            "then again after swapping Response A and Response B. "
            "A response-consistent prediction must flip from A to B "
            "or B to A. If it does not, the result indicates order "
            "sensitivity rather than reliable response preference."
        )

        st.write(
            "Verbosity analysis compares response-length differences "
            "with the predicted winner and reports the longer answer's "
            "win rate and length/prediction correlation."
        )

        st.write(
            "These are diagnostic and mitigation signals, not proof "
            "of causal bias."
        )

    st.divider()

    retraining_panel(
        base,
        "evaluation",
    )


def about_page(
    base: str,
    health: dict[str, Any] | None,
    health_error: str | None,
) -> None:

    st.markdown(
        "## About EvalAI"
    )

    st.caption(
        "Understand the app and check backend readiness in one place."
    )

    status_key, status_title, status_detail = (
        backend_status_summary(
            health,
            health_error,
        )
    )

    if status_key == "online":

        st.success(
            status_title
        )

    elif status_key == "degraded":

        st.warning(
            status_title
        )

    else:

        st.error(
            status_title
        )

    st.caption(
        status_detail
    )

    health_col1, health_col2, health_col3 = (
        st.columns(3)
    )

    with health_col1:

        st.metric(
            "Service status",
            str(
                health.get(
                    "status",
                    "offline",
                )
                if health
                else "offline"
            ).upper(),
        )

    with health_col2:

        st.metric(
            "Model mode",
            (
                "Demo"
                if (health or {}).get(
                    "demo_mode"
                )
                else "Trained"
            ),
        )

    with health_col3:

        st.metric(
            "Model",
            "RoBERTa",
        )

    if st.button(
        "Refresh backend status",
        use_container_width=True,
    ):

        st.rerun()

    st.markdown(
        "### What this app does"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.markdown(
            """
            <div class="about-card">
                <h4>Generate</h4>
                <p>
                    Creates Response A and Response B from two
                    configured Ollama models using the same prompt.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            """
            <div class="about-card">
                <h4>Compare</h4>
                <p>
                    Scores both responses with the trained RoBERTa
                    preference model and predicts which answer is preferred.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:

        st.markdown(
            """
            <div class="about-card">
                <h4>Learn</h4>
                <p>
                    Captures human feedback, analyzes bias, and can
                    validate a new preference-model candidate before activation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "### Backend details"
    )

    st.code(
        base,
        language=None,
    )

    if health and health.get("error"):

        st.caption(
            f"Backend message: {health.get('error')}"
        )

    with st.expander(
        "Prediction contract"
    ):

        st.write(
            "Model output winner is strictly A or B. "
            "Tie is available for human feedback."
        )

        st.code(
            "{prompt}\nResponse: {response}",
            language=None,
        )

    with st.expander(
        "Human-feedback learning"
    ):

        st.write(
            "Human A/B feedback is stored and can be used to "
            "fine-tune a candidate RoBERTa preference model."
        )

        st.write(
            "The candidate is evaluated against the existing "
            "held-out benchmark before it can replace the active model."
        )

        st.write(
            "If the candidate performs worse, the current model remains active."
        )


def main() -> None:

    dark_mode = st.session_state.get(
        "dark_mode",
        True,
    )

    inject_css(
        dark_mode
    )

    backend_url = st.session_state.get(
        "backend_url",
        DEFAULT_API,
    )

    health, health_error = get_health(
        backend_url
    )

    (
        status_key,
        status_title,
        _,
    ) = backend_status_summary(
        health,
        health_error,
    )

    backend_available = (
        status_key == "online"
    )

    theme_col, _ = st.columns(
        [1, 7]
    )

    with theme_col:

        if st.button(
            "☀️ Light mode"
            if dark_mode
            else "🌙 Dark mode",
            key="theme_toggle",
            use_container_width=True,
        ):

            st.session_state[
                "dark_mode"
            ] = not dark_mode

            st.rerun()

    st.markdown(
        """
        <div class="hero">
            <h1>EvalAI</h1>
            <p>
                Human preference prediction for competing LLM responses.
                Compare, understand, and capture human feedback.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if status_key != "online":

        st.warning(
            f"{status_title}. "
            "Check the About tab for details."
        )

    (
        tab_compare,
        tab_feedback,
        tab_evaluation,
        tab_about,
    ) = st.tabs(
        [
            "⚖️ Compare",
            "👤 Human Feedback",
            "📊 Evaluation & Bias",
            "ℹ️ About",
        ]
    )

    with tab_compare:

        compare_page(
            backend_url,
            backend_available=backend_available,
        )

    with tab_feedback:

        feedback_page(
            backend_url
        )

    with tab_evaluation:

        evaluation_page(
            backend_url
        )

    with tab_about:

        about_page(
            backend_url,
            health,
            health_error,
        )


main()