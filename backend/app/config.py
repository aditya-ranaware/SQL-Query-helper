from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # points to backend/


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"

    # Workflow safety limits
    max_fix_attempts: int = 3      # how many times the AI may fix a broken query
    max_result_rows: int = 100     # rows returned to the screen

    # Database
    db_path: Path = BASE_DIR / "data" / "shop.db"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")


settings = Settings()