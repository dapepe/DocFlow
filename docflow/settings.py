from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


class Settings(BaseSettings):
    # App Settings
    docflow_env: str = Field("development", alias="DOCFLOW_ENV")
    docflow_output_dir: str = Field("./output", alias="DOCFLOW_OUTPUT_DIR")
    docflow_log_level: str = Field("INFO", alias="DOCFLOW_LOG_LEVEL")
    docflow_schema_path: str = Field("config/schema.json", alias="DOCFLOW_SCHEMA_PATH")

    # Primary Model
    primary_model: str = Field("qwen-vision", alias="PRIMARY_MODEL")

    # Common Model Settings
    temperature: float = Field(0.2, alias="DOCFLOW_TEMPERATURE")
    max_tokens: int = Field(1000, alias="DOCFLOW_MAX_TOKENS")

    # Ollama Settings
    ollama_host: str = Field("http://localhost:11434", alias="OLLAMA_HOST")
    ollama_timeout: int = Field(60, alias="OLLAMA_TIMEOUT")
    ollama_max_retries: int = Field(3, alias="OLLAMA_MAX_RETRIES")
    ollama_retry_backoff: float = Field(0.3, alias="OLLAMA_RETRY_BACKOFF")

    # OpenRouter Settings
    openrouter_api_key: Optional[str] = Field(None, alias="OPENROUTER_API_KEY")
    openrouter_api_base: str = Field(
        "https://openrouter.ai/api/v1", alias="OPENROUTER_API_BASE"
    )
    openrouter_app_name: str = Field("DocFlow", alias="OPENROUTER_APP_NAME")
    openrouter_site_url: str = Field(
        "https://github.com/docflow/docflow", alias="OPENROUTER_SITE_URL"
    )
    openrouter_timeout: int = Field(120, alias="OPENROUTER_TIMEOUT")
    openrouter_max_retries: int = Field(3, alias="OPENROUTER_MAX_RETRIES")

    # Feature Flags
    auto_ocr: str = Field("smart", alias="DOCFLOW_AUTO_OCR")
    batch_size: int = Field(4, alias="DOCFLOW_BATCH_SIZE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
