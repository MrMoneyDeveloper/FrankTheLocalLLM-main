from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "FrankTheLocalLLM"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    allowed_origins: list[str] = ["*"]
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./app.db"
    model: str = "llama3"
    retrieval_k: int = 8
    chunk_size: int = 512

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
