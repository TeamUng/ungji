from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    LOGTAIL_SOURCE_TOKEN: str = ""
    LOGTAIL_HOST: str = ""
    DISCORD_WEBHOOK_URL: str = ""
    UPSTAGE_API_KEY: str = ""
    UPSTAGE_BASE_URL: str = "https://api.upstage.ai/v1/solar"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # 모델 비교 실험(2026-04-29) 결과 채택된 조합 A 기본값.
    # motivator: TP1·2·3·5 의 동기 코칭. helper: TP4 의 문제 막힘 진단/코칭.
    MOTIVATOR_MODEL: str = "openai/gpt-5.4-mini"
    HELPER_MODEL: str = "google/gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT_SECONDS: int = 60
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "ungji"
    GOOGLE_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""


settings = Settings()
