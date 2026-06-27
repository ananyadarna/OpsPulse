from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    MONGO_URI: str = Field(default="mongodb://localhost:27017")
    MONGO_DB: str = Field(default="opspulse")
    
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    
    # Thresholds & Windows
    DETECTION_WINDOW_SECONDS: int = Field(default=300) # 5 minutes
    DETECTION_MIN_SAMPLES: int = Field(default=10)     # Minimum data points before running Z-Score
    LATENCY_Z_SCORE_THRESHOLD: float = Field(default=3.0)
    
    # Error Spike Settings
    ERROR_SPIKE_WINDOW_SECONDS: int = Field(default=60) # 1 minute current window
    ERROR_SPIKE_THRESHOLD: float = Field(default=2.5)   # Times the rolling mean (e.g. current error rate > 2.5x mean)
    
    # Brute Force Settings
    BRUTE_FORCE_WINDOW_SECONDS: int = Field(default=30)
    BRUTE_FORCE_THRESHOLD: int = Field(default=5)

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

settings = Settings()
