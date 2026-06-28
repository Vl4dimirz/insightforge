"""
Central configuration.

Reads settings from environment variables (and a local .env file if present).
Nothing secret is ever hard-coded here — your Gemini key lives in .env, which
is git-ignored. Copy .env.example to .env and paste your key there.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic reads GEMINI_API_KEY from the environment / .env automatically.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    app_name: str = "InsightForge"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# A single shared settings object the rest of the app imports.
settings = Settings()
