"""
Configuration manager for FloodLens AI backend.
Reads configuration from environment variables and .env file.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Locate root directory containing .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

CACHE_DIR = BASE_DIR / "data" / "cache"
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    # Operating Mode
    DEMO_MODE: bool = Field(
        default_factory=lambda: os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    )
    
    # Server network bindings
    BACKEND_HOST: str = Field(default_factory=lambda: os.getenv("BACKEND_HOST", "127.0.0.1"))
    BACKEND_PORT: int = Field(default_factory=lambda: int(os.getenv("BACKEND_PORT", "8000")))
    FRONTEND_PORT: int = Field(default_factory=lambda: int(os.getenv("FRONTEND_PORT", "5173")))
    
    # Allowed CORS Origins
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
            ).split(",")
            if origin.strip()
        ]
    )

    # Copernicus Data Space Ecosystem (CDSE)
    CDSE_CATALOGUE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "CDSE_CATALOGUE_URL", "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        )
    )
    CDSE_TOKEN_URL: str = Field(
        default_factory=lambda: os.getenv(
            "CDSE_TOKEN_URL", "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        )
    )
    CDSE_DOWNLOAD_URL: str = Field(
        default_factory=lambda: os.getenv(
            "CDSE_DOWNLOAD_URL", "https://zipper.dataspace.copernicus.eu/odata/v1/Products"
        )
    )
    CDSE_USERNAME: str = Field(default_factory=lambda: os.getenv("CDSE_USERNAME", ""))
    CDSE_PASSWORD: str = Field(default_factory=lambda: os.getenv("CDSE_PASSWORD", ""))
    CDSE_CLIENT_ID: str = Field(default_factory=lambda: os.getenv("CDSE_CLIENT_ID", ""))
    CDSE_CLIENT_SECRET: str = Field(default_factory=lambda: os.getenv("CDSE_CLIENT_SECRET", ""))
    CDSE_TIMEOUT_SECONDS: int = Field(default_factory=lambda: int(os.getenv("CDSE_TIMEOUT_SECONDS", "25")))
    CDSE_MAX_RETRIES: int = Field(default_factory=lambda: int(os.getenv("CDSE_MAX_RETRIES", "3")))
    CDSE_MAX_DOWNLOAD_SIZE_MB: int = Field(default_factory=lambda: int(os.getenv("CDSE_MAX_DOWNLOAD_SIZE_MB", "1024")))

    # OpenStreetMap settings
    OSM_SNAPSHOT_DATE: str = Field(default_factory=lambda: os.getenv("OSM_SNAPSHOT_DATE", "2026-07-27"))
    OSM_OVERPASS_ENDPOINT: str = Field(
        default_factory=lambda: os.getenv("OSM_OVERPASS_ENDPOINT", "https://overpass-api.de/api/interpreter")
    )
    OSM_DIRECT_API_ENDPOINT: str = Field(
        default_factory=lambda: os.getenv("OSM_DIRECT_API_ENDPOINT", "https://api.openstreetmap.org/api/0.6")
    )

    # Optional AI Summarizer LLM Configuration
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    LLM_PROVIDER: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini"))

    # Case Study: Trishuli River Basin, Nepal
    DEFAULT_AOI_BBOX: List[float] = Field(
        default_factory=lambda: [
            float(coord.strip())
            for coord in os.getenv("DEFAULT_AOI_BBOX", "85.05,27.75,85.25,27.95").split(",")
        ]
    )
    DEFAULT_EVENT_DATE: str = Field(default_factory=lambda: os.getenv("DEFAULT_EVENT_DATE", "2026-08-04"))

    @property
    def has_cdse_credentials(self) -> bool:
        return bool(self.CDSE_USERNAME and self.CDSE_PASSWORD) or bool(self.CDSE_CLIENT_ID and self.CDSE_CLIENT_SECRET)

    @property
    def has_llm_key(self) -> bool:
        return bool(self.GEMINI_API_KEY or self.OPENAI_API_KEY)


settings = Settings()
