from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "arch_observatory"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    MAX_REPO_SIZE_MB: int = 200
    MAX_FILE_COUNT: int = 5000
    MAX_PY_FILE_COUNT: int = 3000
    CLONE_TIMEOUT_SECONDS: int = 120
    ALLOWED_GIT_HOSTS: list[str] = ["github.com"]
    CC_THRESHOLD: int = 10

    # Smell detection thresholds (Phase 4)
    GOD_CLASS_LOC: int = 500
    GOD_CLASS_METHODS: int = 20
    GOD_CLASS_CE: int = 8
    HOTSPOT_CC: int = 10
    HOTSPOT_MI: float = 50
    UNSTABLE_I: float = 0.7
    PAINFUL_CA: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
