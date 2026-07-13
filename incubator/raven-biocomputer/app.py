import json
import os

import gradio as gr

from raven_biocomputer import BioComputer

computer = BioComputer(os.getenv("RAVEN_BIOCOMPUTER_RUNS", "runs"))


def run(task: str, tool: str, payload: str):
    try:
        return computer.execute(task=task, tool=tool, payload=json.loads(payload))
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


with gr.Blocks(title="Raven BioComputer") as demo:
    gr.Markdown("# 🧬 Raven BioComputer\nA private, auditable biology workstation for AI agents.")
    task = gr.Textbox(
        value="Calculate properties for this demonstration sequence.",
        label="Task",
    )
    tool = gr.Dropdown(
        [item["name"] for item in computer.tools.list()],
        value="sequence_stats",
        label="Tool",
    )
    payload = gr.Code(
        value='{"sequence":"ACGTACGTNN"}',
        language="json",
        label="Payload",
    )
    output = gr.JSON(label="Raven run receipt")
    gr.Button("Run").click(run, [task, tool, payload], output)
    gr.Markdown("Dry-lab demo only. No clinical advice or autonomous wet-lab control.")

if __name__ == "__main__":
    demo.launch()
