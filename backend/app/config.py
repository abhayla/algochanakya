from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AlgoChanakya"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Kite Connect (Zerodha)
    KITE_API_KEY: str
    KITE_API_SECRET: str
    KITE_REDIRECT_URL: str

    # AngelOne SmartAPI (optional - for market data)
    ANGEL_API_KEY: str = ""  # For live data (WebSocket)
    ANGEL_API_SECRET: str = ""  # Secret for live data API
    ANGEL_HIST_API_KEY: str = ""  # For historical data
    ANGEL_HIST_API_SECRET: str = ""  # Secret for historical data API
    ANGEL_TRADE_API_KEY: str = ""  # For trading API
    ANGEL_TRADE_API_SECRET: str = ""  # Secret for trading API
    ANGEL_API_KEY_HISTORICAL: str = ""  # Alias for ANGEL_HIST_API_KEY (legacy)

    # Frontend
    FRONTEND_URL: str

    # Anthropic Claude API (for AI features)
    ANTHROPIC_API_KEY: str

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
