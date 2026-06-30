import gradio as gr
import json

# Demo mode — showcases what Raven AI does without requiring full runtime
DEMO_AGENTS = {
    "Raven Bio 🧬": {
        "description": "Genomics, proteomics, transcriptomics, wet-lab planning",
        "examples": [
            "Analyze BRCA1 variant pathogenicity",
            "Design PCR primers for SARS-CoV-2 detection",
            "What is the protein structure of ACE2?",
            "Plan a CRISPR knockout experiment for TP53"
        ]
    },
    "Raven Clinical 🏥": {
        "description": "Healthcare evidence, clinical calculators, PHI-aware workflows",
        "examples": [
            "Calculate Wells score for DVT probability",
            "Summarize evidence for metformin in T2DM",
            "Drug interaction check: warfarin + aspirin",
            "CURB-65 score for pneumonia severity"
        ]
    },
    "Raven Research 📚": {
        "description": "Literature review, citation verification, hypothesis generation",
        "examples": [
            "Find recent papers on CRISPR base editing",
            "Summarize the latest Alzheimer's drug trials",
            "Generate hypothesis: gut microbiome and depression",
            "Verify this citation: Smith et al. 2024 Nature"
        ]
    },
    "Raven LabOps 🔬": {
        "description": "Protocol execution, sample tracking, instrument coordination",
        "examples": [
            "Create an RNA extraction protocol for 96 samples",
            "Track sample QC for batch #2024-A",
            "Schedule instrument maintenance for HPLC",
            "Generate audit log for clinical trial samples"
        ]
    }
}

DEMO_RESPONSES = {
    "Raven Bio 🧬": "🧬 **Raven Bio Analysis**\n\nThis is a demo response. In production, Raven Bio would:\n- Query ClinVar, gnomAD, and UniProt databases\n- Run protein structure prediction via ESMFold\n- Cross-reference with OMIM and ClinGen\n- Generate a structured clinical/research report\n\n*Deploy Raven AI locally for full functionality: `pip install raven-ai`*",
    "Raven Clinical 🏥": "🏥 **Raven Clinical Response**\n\nThis is a demo response. In production, Raven Clinical would:\n- Apply validated clinical scoring algorithms\n- Cross-reference UpToDate and Cochrane evidence\n- Flag drug interactions against DrugBank\n- Generate a PHIPA-compliant clinical note\n\n*Deploy for your healthcare org: `docker pull simpliibarrii-crypto/raven-ai`*",
    "Raven Research 📚": "📚 **Raven Research Response**\n\nThis is a demo response. In production, Raven Research would:\n- Search PubMed, arXiv, bioRxiv with semantic queries\n- Verify citations against CrossRef\n- Generate structured literature summaries with evidence levels\n- Export citations in BibTeX / EndNote format\n\n*Try locally: `pip install raven-ai && raven research \"your query\"`*",
    "Raven LabOps 🔬": "🔬 **Raven LabOps Response**\n\nThis is a demo response. In production, Raven LabOps would:\n- Generate SOP-compliant protocols\n- Create LIMS-compatible sample tracking entries\n- Schedule instrument calibration and maintenance\n- Generate 21 CFR Part 11 compliant audit logs\n\n*Already deployed at Gary J Armstrong Retirement Home, Ottawa.*"
}

def respond(message, agent, history):
    response = DEMO_RESPONSES.get(agent, "Demo response — deploy locally for full functionality.")
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return history, history, ""

with gr.Blocks(title="Raven AI — Biology & Healthcare Agent", theme=gr.themes.Soft()) as app:
    gr.Markdown("""
    # 🦅 Raven AI — Open Source Biology & Healthcare Agent
    
    **Sovereign, local-first AI for labs, clinics, and research teams.**
    
    > Already deployed at Gary J Armstrong Retirement Home (Ottawa) · Apache 2.0 License
    
    | Agent | Use Case |
    |-------|----------|
    | Raven Bio 🧬 | Genomics, proteomics, wet-lab planning |
    | Raven Clinical 🏥 | Clinical evidence, calculators, PHI workflows |
    | Raven Research 📚 | Literature review, hypothesis generation |
    | Raven LabOps 🔬 | Protocol execution, sample tracking, audit logs |
    """)
    
    agent_dd = gr.Dropdown(choices=list(DEMO_AGENTS.keys()), value="Raven Bio 🧬", label="Select Agent")
    
    @gr.render(inputs=agent_dd)
    def show_examples(agent):
        agent_info = DEMO_AGENTS.get(agent, {})
        gr.Markdown(f"**{agent_info.get('description', '')}**")
    
    chatbot = gr.Chatbot(type="messages", height=450)
    msg = gr.Textbox(placeholder="Ask Raven AI anything...", label="Your question")
    
    with gr.Row():
        send_btn = gr.Button("Ask Raven", variant="primary")
        clear_btn = gr.Button("Clear")
    
    state = gr.State([])
    send_btn.click(respond, [msg, agent_dd, state], [chatbot, state, msg])
    msg.submit(respond, [msg, agent_dd, state], [chatbot, state, msg])
    clear_btn.click(lambda: ([], []), outputs=[chatbot, state])
    
    gr.Markdown("""
    ---
    **Deploy Raven AI for your organization:**
    ```bash
    pip install raven-ai
    raven serve --port 8000
    ```
    [GitHub](https://github.com/simpliibarrii-crypto/raven-ai) · [Documentation](https://github.com/simpliibarrii-crypto/raven-ai/docs)
    """)

app.launch()
