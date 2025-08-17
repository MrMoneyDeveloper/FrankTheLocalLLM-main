import os
import socket
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "hello"}

def get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]

if __name__ == "__main__":
    port = get_free_port()
    print(port, flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
