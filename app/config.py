from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    nvidia_api_key: str
    nvidia_model: str = "meta/llama-3.1-8b-instruct"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    encryption_key: str
    secret_key: str

    # Logging / Axiom (optional — logs go to stdout only when token is unset)
    axiom_token: str | None = None
    axiom_dataset: str = "velora"
    axiom_org_id: str | None = None
    log_level: str = "INFO"
    app_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
