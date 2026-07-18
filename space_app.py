from __future__ import annotations

import html

import gradio as gr


WORKFLOWS = {
    "Raven Research": {
        "role": "Evidence review and citation trace",
        "route": "question → source packet → claims → verification → review",
        "example": "Compare the strength of evidence across three public research summaries.",
    },
    "Raven Bio": {
        "role": "Bounded computational-biology workflow",
        "route": "task → registered tool → artifact → evidence receipt → review",
        "example": "Create an auditable plan for reviewing a public sequence-statistics result.",
    },
    "Raven Clinical": {
        "role": "Consent-aware documentation prototype",
        "route": "consent → structured observations → draft → human review → audit",
        "example": "Turn synthetic care observations into a reviewable handoff outline.",
    },
    "Raven LabOps": {
        "role": "Reproducible run and protocol records",
        "route": "request → safety gate → bounded action → artifacts → run manifest",
        "example": "Outline the metadata needed to reproduce a harmless dry-lab computation.",
    },
}

BRAND_CSS = """
:root {
  --obsidian:#050505;--carbon:#0d0d0f;--graphite:#151518;--crimson:#c8273f;
  --crimson-bright:#f04460;--champagne:#c9ad7d;--champagne-light:#e7d3af;
  --ivory:#f4efe7;--ash:#8f8a83;--ash-light:#b8b0a5;--positive:#78d7a0;
}
body { background:#050505 !important; }
.gradio-container {
  max-width:1120px !important;margin:0 auto !important;padding:28px !important;
  color-scheme:dark !important;color:var(--ivory) !important;
  font-family:"Avenir Next",Inter,system-ui,sans-serif !important;
  background:radial-gradient(circle at 88% 0%,rgba(200,39,63,.18),transparent 30rem),
             radial-gradient(circle at 4% 35%,rgba(201,173,125,.055),transparent 26rem),#050505 !important;
}
.raven-hero { position:relative;overflow:hidden;margin-bottom:18px;padding:clamp(24px,5vw,48px);
  border:1px solid rgba(201,173,125,.18);border-radius:22px;
  background:linear-gradient(145deg,rgba(21,21,24,.96),rgba(7,7,8,.98));
  box-shadow:0 28px 80px rgba(0,0,0,.48),0 0 38px rgba(200,39,63,.07); }
.raven-hero::after { content:"";position:absolute;right:-65px;top:-75px;width:290px;height:290px;
  border:1px solid rgba(201,173,125,.16);border-radius:50%;box-shadow:inset 0 0 0 50px rgba(200,39,63,.025); }
.raven-kicker { color:var(--crimson-bright);font:700 .72rem ui-monospace,Menlo,monospace;letter-spacing:.18em; }
.raven-hero h1 { margin:12px 0 9px;color:var(--ivory);font:600 clamp(2.3rem,6vw,5rem)/.96 Georgia,serif;letter-spacing:-.055em; }
.raven-hero h1 span { color:var(--champagne); }
.raven-hero p { max-width:830px;margin:0;color:var(--ash-light); }
.raven-meta { display:flex;flex-wrap:wrap;gap:8px;margin-top:22px; }
.raven-meta span { padding:7px 10px;border:1px solid rgba(201,173,125,.17);border-radius:999px;
  background:rgba(5,5,5,.56);color:var(--ash);font:.68rem ui-monospace,Menlo,monospace; }
.disclosure { margin:0 0 18px;padding:14px 17px;border-left:3px solid var(--crimson);
  background:rgba(200,39,63,.045);color:var(--ash-light); }
.disclosure strong { color:var(--champagne-light); }
.gradio-container .block,.gradio-container .form,.gradio-container .panel {
  border-color:rgba(201,173,125,.16) !important;border-radius:15px !important;
  background:rgba(21,21,24,.9) !important;box-shadow:none !important; }
.gradio-container label,.gradio-container .label-wrap { color:var(--champagne-light) !important; }
.gradio-container input,.gradio-container textarea { border-color:rgba(201,173,125,.16) !important;
  background:#080809 !important;color:var(--ivory) !important; }
.gradio-container input:focus,.gradio-container textarea:focus { border-color:var(--champagne) !important;
  box-shadow:0 0 0 3px rgba(201,173,125,.09) !important; }
.gradio-container button.primary { border:1px solid var(--crimson-bright) !important;
  background:linear-gradient(180deg,var(--crimson-bright),var(--crimson)) !important;
  color:#fff8f5 !important;font-weight:700 !important; }
.gradio-container button.secondary { border:1px solid rgba(201,173,125,.3) !important;
  background:var(--graphite) !important;color:var(--champagne-light) !important; }
.workflow-card { margin:0 0 18px;padding:16px 18px;border:1px solid rgba(201,173,125,.16);
  border-radius:14px;background:rgba(13,13,15,.8);color:var(--ash-light); }
.workflow-card strong { color:var(--champagne-light); }
@media(max-width:640px){.gradio-container{padding:12px!important}.raven-hero{padding:25px 19px}}
"""


def workflow_summary(workflow: str) -> str:
    info = WORKFLOWS[workflow]
    return (
        f'<div class="workflow-card"><strong>{html.escape(info["role"])}</strong><br>'
        f'<span>{html.escape(info["route"])}</span><br><br>'
        f'<small>Example: {html.escape(info["example"])}</small></div>'
    )


def respond(message: str, workflow: str, history: list[dict] | None):
    history = list(history or [])
    question = (message or "").strip() or WORKFLOWS[workflow]["example"]
    info = WORKFLOWS[workflow]
    response = (
        f"**{workflow} demonstration**\n\n"
        f"**Question received:** {question}\n\n"
        f"**Bounded route:** {info['route']}\n\n"
        "**Illustrative evidence receipt**\n"
        "- Source state: demonstration packet, not live retrieval\n"
        "- Claim state: draft only\n"
        "- Verification: required before publication or care use\n"
        "- Risk: human review required\n"
        "- Export: no patient data, credentials, or private files\n\n"
        "This deterministic public demo explains Raven's workflow contracts. "
        "It does not query live scientific databases, provide clinical advice, "
        "perform wet-lab actions, or demonstrate a trained model's accuracy."
    )
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": response})
    return history, history, ""


with gr.Blocks(title="Raven AI — Evidence-linked Scientific Intelligence", css=BRAND_CSS) as app:
    gr.HTML(
        """
        <section class="raven-hero">
          <div class="raven-kicker">RAVEN ECOSYSTEM / SCIENTIFIC INTELLIGENCE CORE</div>
          <h1>Raven <span>AI</span></h1>
          <p>Explore an evidence-aware agent workflow built around sources, claims, verification, reproducible records, safety gates, and visible human authority.</p>
          <div class="raven-meta"><span>ACTIVE RESEARCH PLATFORM</span><span>EVIDENCE-LINKED</span><span>HUMAN REVIEW REQUIRED</span></div>
        </section>
        <div class="disclosure"><strong>Public workflow demonstration.</strong> Outputs are deterministic illustrations of system contracts, not live research, medical guidance, or autonomous science.</div>
        """
    )

    workflow = gr.Dropdown(
        choices=list(WORKFLOWS),
        value="Raven Research",
        label="Workflow",
    )
    summary = gr.HTML(value=workflow_summary("Raven Research"))
    workflow.change(workflow_summary, inputs=workflow, outputs=summary)

    chatbot = gr.Chatbot(type="messages", height=430, label="Evidence workflow")
    message = gr.Textbox(
        placeholder="Describe a research or workflow question...",
        label="Question",
    )

    with gr.Row():
        run = gr.Button("Build demonstration trace", variant="primary")
        clear = gr.Button("Clear", variant="secondary")

    state = gr.State([])
    run.click(respond, [message, workflow, state], [chatbot, state, message])
    message.submit(respond, [message, workflow, state], [chatbot, state, message])
    clear.click(lambda: ([], []), outputs=[chatbot, state])


if __name__ == "__main__":
    app.launch()
