from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "FrankTheLocalLLM"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:5173", "tauri://localhost"]
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./app.db"
    model: str = "llama3"
    model_backend: str = "ollama"
    embed_model: str = "nomic-embed-text"
    retrieval_k: int = 8
    chunk_size: int = 512
    secret_key: str = "super-secret-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
