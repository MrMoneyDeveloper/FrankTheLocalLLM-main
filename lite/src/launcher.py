import os
import threading
from dotenv import load_dotenv
from .bootstrap import bootstrap, find_available_port, free_port
from .ui import build_ui

load_dotenv()


def start_api_in_thread(host: str, port: int):
    import uvicorn
    from .app import app

    def _run():
        uvicorn.run(app, host=host, port=port, reload=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def main():
    bootstrap()

    # Backend
    start_api = os.getenv("START_API", "1") == "1"
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8001"))
    if start_api:
        try:
            free_port(port)
            port = find_available_port(port)
        except Exception:
            port = find_available_port(port)
        start_api_in_thread(host, port)
        print(f"API running at http://{host}:{port}")

    # UI
    ui_port = int(os.getenv("UI_PORT", "7860"))
    try:
        free_port(ui_port)
        ui_port = find_available_port(ui_port)
    except Exception:
        pass
    demo = build_ui()
    print(f"UI running at http://127.0.0.1:{ui_port}")
    demo.launch(server_name="127.0.0.1", server_port=ui_port, show_error=True)


if __name__ == "__main__":
    main()

