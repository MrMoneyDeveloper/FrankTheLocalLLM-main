import os
import gradio as gr
from dotenv import load_dotenv
from .ollama_client import chat as ollama_chat
from .vectorstore import query as vs_query

load_dotenv()


def ask_llm(prompt: str) -> str:
    return ollama_chat([{"role": "user", "content": prompt}])


def search_docs(q: str):
    return vs_query(q)


def build_ui():
    with gr.Blocks(title="Local LLM (Lite)") as demo:
        gr.Markdown("# Frank Local LLM — Python + Ollama (Lite)")
        with gr.Tab("Chat"):
            inp = gr.Textbox(label="Prompt", lines=4)
            out = gr.Textbox(label="Answer")
            btn = gr.Button("Ask")
            btn.click(fn=ask_llm, inputs=inp, outputs=out)
        with gr.Tab("Search"):
            q = gr.Textbox(label="Query")
            res = gr.JSON(label="Top Matches")
            gr.Button("Search").click(fn=search_docs, inputs=q, outputs=res)
    return demo


if __name__ == "__main__":
    demo = build_ui()
    ui_port = int(os.getenv("UI_PORT", "7860"))
    # Try to free or auto-increment port
    try:
        from .bootstrap import free_port, find_available_port

        free_port(ui_port)
        ui_port = find_available_port(ui_port)
    except Exception:
        pass
    demo.launch(server_name="127.0.0.1", server_port=ui_port, show_error=True)

