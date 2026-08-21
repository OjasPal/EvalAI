import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(
    page_title="EvalAI — Human Preference AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_API = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap');

        :root {
            --brand-teal: #0f6b6a;
            --brand-orange: #d96a3b;
            --surface: #dbeaf4;
            --text: #1a1f24;
            --muted: #5b6670;
            --heading: #14242f;
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

        #MainMenu, header, footer,
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
            border: 1px solid rgba(58, 128, 173, .55);
            margin-bottom: 1.2rem;
            background: #4f94c2;
            box-shadow: 0 12px 34px rgba(31, 73, 108, .24);
        }

        .hero h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #f5f8f8;
            text-shadow: 0 2px 10px rgba(0,0,0,.18);
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
            background: rgba(38,112,112,.1);
        }

        .response-heading.a {
            border-left: 4px solid var(--brand-teal);
        }

        .response-heading.b {
            border-left: 4px solid var(--brand-orange);
            background: rgba(224,107,60,.1);
        }

        .winner-card {
            padding: 1.35rem;
            border-radius: 10px;
            border: 1px solid rgba(224,107,60,.35);
            margin: .8rem 0 1rem;
            background: linear-gradient(110deg, rgba(224,107,60,.16), rgba(79,148,194,.12));
        }

        .winner-card h2 {
            margin: 0;
            font-size: 1.38rem;
            font-weight: 800;
            color: #2b2b2b;
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
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 10px;
            padding: .68rem;
            background: rgba(69, 123, 161, .12);
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
            color: #182b34;
        }

        div.stButton > button {
            min-height: 2.8rem;
            border-radius: 10px;
            font-weight: 700;
            letter-spacing: .01em;
            font-size: .97rem;
        }

        [data-testid="stTabs"] {
            margin-top: .2rem;
            margin-bottom: .85rem;
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: .55rem;
            padding: .35rem;
            border: 1px solid rgba(65, 98, 117, .18);
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(89, 145, 183, .26), rgba(62, 120, 161, .24));
        }

        [data-testid="stTabs"] button {
            font-weight: 730;
            font-size: .95rem;
            letter-spacing: .01em;
            color: #2d4551;
            border-radius: 10px;
            border: 1px solid transparent;
            padding: .55rem .88rem;
            background: rgba(55, 101, 138, .2);
            transition: all .2s ease;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #0f4f66;
            background: linear-gradient(180deg, rgba(116, 170, 206, .95), rgba(91, 149, 188, .95));
            border-color: rgba(30, 105, 139, .28);
            box-shadow: 0 4px 12px rgba(34, 86, 112, .12);
            font-weight: 780;
        }

        [data-testid="stTabs"] button:hover {
            color: #163d4e;
            background: rgba(98, 154, 192, .42);
            border-color: rgba(33, 92, 121, .22);
        }

        .stTextArea textarea {
            font-size: .98rem;
            line-height: 1.58;
            color: #f4f8fa !important;
            -webkit-text-fill-color: #f4f8fa;
            background: #668595 !important;
            caret-color: #0f6b6a;
            border: 1px solid #9aaeb8;
        }

        .stTextArea textarea::placeholder {
            color: #dce8ed !important;
            -webkit-text-fill-color: #dce8ed;
            opacity: 1;
        }

        .stTextArea textarea:focus {
            border-color: #0f6b6a;
            box-shadow: 0 0 0 2px rgba(15, 107, 106, .18);
        }

        .stRadio label {
            font-weight: 600;
            color: #1f3139;
        }

        .about-card {
            border: 1px solid rgba(128,128,128,.2);
            border-radius: 14px;
            padding: 1rem;
            background: rgba(79, 148, 194, .14);
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def post_json(base: str, path: str, payload: dict[str, Any], timeout: int = 180):
    try:
        response = requests.post(
            api_url(base, path),
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        return None, f"Could not connect to FastAPI: {exc}"

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return None, f"Backend returned HTTP {response.status_code}: {detail}"

    try:
        return response.json(), None
    except ValueError:
        return None, "Backend returned an invalid JSON response."


def get_health(base: str):
    try:
        response = requests.get(api_url(base, "/health"), timeout=30)
    except requests.RequestException as exc:
        return None, str(exc)

    if not response.ok:
        return None, f"HTTP {response.status_code}"

    try:
        return response.json(), None
    except ValueError:
        return None, "Invalid JSON response."


def score_bar(label: str, score: float) -> None:
    st.markdown(f"**{label} — {score:.1%}**")
    st.progress(max(0.0, min(1.0, score)))


def prediction_values(data: Any) -> tuple[str, float, float, float] | None:
    if not isinstance(data, dict):
        return None

    winner = data.get("winner")
    if winner not in {"A", "B"}:
        return None

    try:
        confidence = float(data["confidence"])
        score_a = float(data["score_a"])
        score_b = float(data["score_b"])
    except (KeyError, TypeError, ValueError):
        return None

    if not all(0.0 <= score <= 1.0 for score in (score_a, score_b, confidence)):
        return None

    return winner, confidence, score_a, score_b


def backend_status_summary(health: dict[str, Any] | None, error: str | None) -> tuple[str, str, str]:
    if health is None:
        return "offline", "Backend offline", error or "Could not reach the backend service."

    status = str(health.get("status", "unknown")).lower()
    if status == "ok":
        return "online", "Backend online", "API and model are ready."
    if status == "degraded":
        return "degraded", "Backend degraded", str(health.get("error", "Model is unavailable."))
    return "starting", "Backend starting", "Service is up but still initializing."


def compare_page(base: str, backend_available: bool) -> None:
    st.markdown("## Compare two LLM responses")
    st.caption(
        "Give the same user prompt and two competing responses. "
        "EvalAI predicts which response a human is more likely to prefer."
    )

    st.markdown(
        '<div class="workflow-note"><b>Workflow:</b> enter a prompt, generate or paste two answers, then compare them with the trained reward model.</div>',
        unsafe_allow_html=True,
    )

    prompt = st.text_area(
        "User prompt",
        height=120,
        placeholder="Example: Explain quantum computing in simple terms.",
    )

    generated_prompt = st.session_state.get("generated_prompt")
    if generated_prompt and generated_prompt != prompt:
        st.info("The prompt changed. Generate new responses before comparing.")

    generate = st.button(
        "Generate two responses",
        type="secondary",
        use_container_width=True,
        disabled=not backend_available,
    )

    if not backend_available:
        st.warning("Backend is not ready yet. Open the About tab to check live backend status.")

    if generate:
        if not prompt.strip():
            st.warning("Enter a user prompt before generating responses.")
        else:
            with st.spinner("Generating two responses with Ollama..."):
                generated, error = post_json(
                    base,
                    "/generate",
                    {"prompt": prompt},
                )

            if error:
                st.error(error)
            else:
                st.session_state["generated_response_a"] = generated["response_a"]
                st.session_state["generated_response_b"] = generated["response_b"]
                st.session_state["generated_prompt"] = prompt.strip()
                st.session_state.pop("last_prediction", None)
                st.session_state.pop("last_input", None)
                st.rerun()

    response_a_default = st.session_state.get("generated_response_a", "")
    response_b_default = st.session_state.get("generated_response_b", "")

    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown('<div class="response-heading a">Response A</div>', unsafe_allow_html=True)
        response_a = st.text_area(
            "Response A text",
            height=260,
            placeholder="Paste the first LLM response...",
            value=response_a_default,
            label_visibility="collapsed",
        )

    with col_b:
        st.markdown('<div class="response-heading b">Response B</div>', unsafe_allow_html=True)
        response_b = st.text_area(
            "Response B text",
            height=260,
            placeholder="Paste the second LLM response...",
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
            st.warning("Please provide the prompt, Response A, and Response B.")
            return
        if generated_prompt and generated_prompt != prompt.strip():
            st.warning("Generate new responses for the changed prompt before comparing.")
            return

        with st.spinner("Running preference model..."):
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

        st.session_state["last_prediction"] = data
        st.session_state["last_input"] = {
            "prompt": prompt,
            "response_a": response_a,
            "response_b": response_b,
        }

    data = st.session_state.get("last_prediction")
    if not data:
        return

    st.divider()
    st.markdown("## AI preference prediction")

    values = prediction_values(data)
    if values is None:
        st.error("FastAPI returned an invalid prediction response.")
        return

    winner, confidence, score_a, score_b = values

    if winner == "A":
        headline = "Response A is predicted to be preferred"
    elif winner == "B":
        headline = "Response B is predicted to be preferred"

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
    metric_a.metric("Response A", f"{score_a:.1%}")
    metric_b.metric("Response B", f"{score_b:.1%}")
    metric_c.metric("Confidence", f"{confidence:.1%}")

    st.markdown("### Preference scores")
    score_bar("Response A", score_a)
    score_bar("Response B", score_b)

    if data.get("demo_mode"):
        st.info(
            "Demo mode is active. These scores are placeholders for integration "
            "testing, not real model predictions."
        )

    st.caption(f"Model: {data.get('model', 'unknown')}")


def feedback_page(base: str, compact: bool = False) -> None:
    if not compact:
        st.markdown("## Human feedback")
        st.caption(
            "Human preference can be captured after an AI prediction. "
            "The prototype stores feedback for later analysis."
        )

    prediction = st.session_state.get("last_prediction")
    inputs = st.session_state.get("last_input")

    if not prediction or not inputs:
        st.info("Run a comparison first, then return here to record your preference.")
        return

    st.markdown(
        '<div class="workflow-note"><b>Review the prediction:</b> choose the response you would prefer as a human evaluator.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Your preference")
    choice = st.radio(
        "Human preference",
        ["A", "B", "Tie"],
        horizontal=True,
        key="human_preference_compact" if compact else "human_preference_page",
        label_visibility="collapsed",
    )

    if st.button(
        "Submit human preference",
        type="secondary",
        key="submit_feedback_compact" if compact else "submit_feedback_page",
    ):
        payload = {
            "request_id": prediction.get("request_id"),
            **inputs,
            "human_preference": choice,
        }

        with st.spinner("Saving feedback..."):
            data, error = post_json(base, "/feedback", payload, timeout=20)

        if error:
            st.error(error)
        else:
            st.success("Feedback saved successfully.")


def evaluation_page(base: str) -> None:
    st.markdown("## Evaluation & bias analysis")
    st.caption(
        "Run the trained RoBERTa reward model against the read-only held-out "
        "test split. This is separate from live preference predictions."
    )

    st.info(
        "A full run evaluates every pair in preprocess/test.csv twice: in its "
        "original order and with Response A/B swapped. It can take several "
        "minutes on CPU. Results are calculated live and kept only in this "
        "browser session."
    )

    if st.button(
        "Run held-out evaluation",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner(
            "Evaluating the held-out split and running position/verbosity checks..."
        ):
            data, error = post_json(base, "/evaluation", {}, timeout=3600)

        if error:
            st.error(error)
        else:
            st.session_state["evaluation_result"] = data

    data = st.session_state.get("evaluation_result")
    if not isinstance(data, dict):
        st.warning(
            "No held-out evaluation has been run in this session. Results will "
            "appear here only after the trained model completes an evaluation."
        )
        return

    metrics = data.get("metrics")
    position = data.get("position_bias")
    verbosity = data.get("verbosity_bias")
    if not all(isinstance(section, dict) for section in (metrics, position, verbosity)):
        st.error("FastAPI returned an invalid evaluation response.")
        return

    def percent(value: Any) -> str:
        try:
            return f"{float(value):.1%}"
        except (TypeError, ValueError):
            return "Not available"

    def signed_percent(value: Any) -> str:
        try:
            return f"{float(value):+.1%}"
        except (TypeError, ValueError):
            return "Not available"

    st.success(
        f"Evaluated {data.get('examples_evaluated', 'the available')} held-out "
        f"pairs with {data.get('model', 'the configured')} model."
    )

    st.markdown("### Benchmark metrics")
    st.caption(
        "Precision, recall, and F1 use macro averaging so A-preferred and "
        "B-preferred labels receive equal weight."
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Accuracy", percent(metrics.get("accuracy")))
    c2.metric("Precision", percent(metrics.get("precision")))
    c3.metric("Recall", percent(metrics.get("recall")))
    c4.metric("F1-score", percent(metrics.get("f1")))
    c5.metric("ROC-AUC", percent(metrics.get("roc_auc")))

    if metrics.get("roc_auc") is None and metrics.get("roc_auc_reason"):
        st.caption(str(metrics["roc_auc_reason"]))

    matrix = metrics.get("confusion_matrix")
    if (
        isinstance(matrix, list)
        and len(matrix) == 2
        and all(isinstance(row, list) and len(row) == 2 for row in matrix)
    ):
        st.markdown("#### Confusion matrix")
        st.code(
            "                 Predicted A   Predicted B\n"
            f"Actual A             {matrix[0][0]:>6}        {matrix[0][1]:>6}\n"
            f"Actual B             {matrix[1][0]:>6}        {matrix[1][1]:>6}",
            language=None,
        )

    class_metrics = metrics.get("class_metrics")
    if isinstance(class_metrics, dict):
        st.markdown("#### Per-class metrics")
        class_a, class_b = st.columns(2)
        for column, label in ((class_a, "A"), (class_b, "B")):
            values = class_metrics.get(label)
            if isinstance(values, dict):
                with column:
                    st.caption(
                        f"Response {label} preferred "
                        f"(support: {values.get('support', 'not available')})"
                    )
                    st.write(
                        f"Precision {percent(values.get('precision'))} · "
                        f"Recall {percent(values.get('recall'))} · "
                        f"F1 {percent(values.get('f1'))}"
                    )

    st.caption(f"Source: {data.get('dataset', 'preprocess/test.csv')}")

    st.markdown("### Bias checks")
    st.caption("These checks measure whether ordering or answer length affects model preference.")
    b1, b2 = st.columns(2)
    with b1:
        st.markdown("#### Position bias")
        st.metric(
            "Inconsistent swap rate",
            percent(position.get("inconsistent_swap_rate")),
        )
        st.caption(
            f"{position.get('inconsistent_swaps', 'Not available')} of "
            f"{position.get('pairs_evaluated', 'Not available')} pairs did not "
            "flip to the corresponding response after A/B order was reversed."
        )
        st.caption(
            "Combined first-position win rate: "
            f"{percent(position.get('combined_first_position_win_rate'))}. "
            "A value near 50% is the order-neutral reference."
        )
    with b2:
        st.markdown("#### Verbosity bias")
        st.metric(
            "Longer response win rate",
            percent(verbosity.get("longer_response_win_rate")),
            signed_percent(verbosity.get("longer_response_win_rate_excess_over_chance")),
        )
        st.caption(
            f"Longer response won {verbosity.get('longer_response_wins', 'not available')} "
            f"of {verbosity.get('pairs_with_different_lengths', 'not available')} "
            "pairs with different response lengths. Delta is relative to a 50% baseline."
        )
        correlation = verbosity.get("length_delta_prediction_correlation")
        if correlation is None:
            st.caption(str(verbosity.get("correlation_reason", "Correlation not available.")))
        else:
            st.caption(
                "Length-delta/prediction correlation: "
                f"{float(correlation):+.3f}. Negative values mean the longer "
                "Response A is more often selected."
            )

    with st.expander("How the checks work"):
        st.write(
            "The model is scored on the original test pairs for the benchmark "
            "metrics. Each pair is then scored again after swapping Response A "
            "and Response B; a response-consistent prediction must flip from A "
            "to B (or B to A). For verbosity, EvalAI compares response length "
            "differences with the predicted winner and reports both the longer "
            "answer's win rate and a Pearson correlation. These are diagnostic "
            "signals, not proof of a causal bias."
        )


def about_page(base: str, health: dict[str, Any] | None, health_error: str | None) -> None:
    st.markdown("## About EvalAI")
    st.caption("Understand the app and check backend readiness in one place.")

    status_key, status_title, status_detail = backend_status_summary(health, health_error)
    if status_key == "online":
        st.success(status_title)
    elif status_key == "degraded":
        st.warning(status_title)
    else:
        st.error(status_title)
    st.caption(status_detail)

    health_col1, health_col2, health_col3 = st.columns(3)
    with health_col1:
        st.metric("Service status", str(health.get("status", "offline") if health else "offline").upper())
    with health_col2:
        st.metric("Model mode", "Demo" if (health or {}).get("demo_mode") else "Trained")
    with health_col3:
        st.metric("Model", str((health or {}).get("model", "Not available")))

    if st.button("Refresh backend status", use_container_width=True):
        st.rerun()

    st.markdown("### What this app does")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="about-card"><h4>Generate</h4><p>Creates Response A and Response B from two configured Ollama models using the same user prompt.</p></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="about-card"><h4>Compare</h4><p>Scores each response with the trained reward model and predicts which answer is preferred.</p></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="about-card"><h4>Learn</h4><p>Captures human feedback and runs held-out evaluation to inspect quality and bias behavior.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Backend details")
    st.code(base, language=None)
    if health and health.get("error"):
        st.caption(f"Backend message: {health.get('error')}")

    with st.expander("Prediction contract"):
        st.write("Model output winner is strictly A or B. Tie is only available for human feedback.")
        st.code("{prompt}\nResponse: {response}", language=None)


def main() -> None:
    inject_css()

    backend_url = st.session_state.get("backend_url", DEFAULT_API)
    health, health_error = get_health(backend_url)
    status_key, status_title, _ = backend_status_summary(health, health_error)
    backend_available = status_key == "online"

    st.markdown(
        f"""
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
        st.warning(f"{status_title}. Check the About tab for details.")

    tab_compare, tab_feedback, tab_evaluation, tab_about = st.tabs(
        ["⚖️ Compare", "👤 Human Feedback", "📊 Evaluation & Bias", "ℹ️ About"]
    )

    with tab_compare:
        compare_page(backend_url, backend_available=backend_available)

    with tab_feedback:
        feedback_page(backend_url)

    with tab_evaluation:
        evaluation_page(backend_url)

    with tab_about:
        about_page(backend_url, health, health_error)


main()
