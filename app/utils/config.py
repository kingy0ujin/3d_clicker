"""
Application Configuration Management
"""

import os
import logging
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class AppConfig:
    """Application configuration from environment variables."""

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")

    # API Endpoints
    HF_INFERENCE_API_URL: str = os.getenv(
        "HF_INFERENCE_API_URL",
        "https://api-inference.huggingface.co"
    )

    # Application Settings
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Streamlit Settings
    STREAMLIT_SERVER_PORT: int = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    STREAMLIT_SERVER_HOST: str = os.getenv("STREAMLIT_SERVER_HOST", "localhost")

    # File Upload Settings
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FORMATS: list = ["png", "jpg", "jpeg", "webp"]

    # 3D Processing Settings
    MAX_MESH_VERTICES: int = 100000
    MESH_SIMPLIFICATION_TARGET: int = 50000
    BASE_KEYCAP_MODEL_SOURCE: str = os.getenv(
        "BASE_KEYCAP_MODEL_SOURCE",
        str(Path(__file__).resolve().parents[1] / "assets" / "base_keycap.stl")
    )

    # Timeout Settings (seconds)
    OPENAI_TIMEOUT: int = 60
    HUGGINGFACE_TIMEOUT: int = 120
    API_RETRY_ATTEMPTS: int = 3

    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration.
        
        Returns:
            True if all required configs are set
            
        Raises:
            ValueError: If critical configs are missing
        """
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        # HF_API_TOKEN is optional (TripoSR is now run locally)
        # GPU is recommended for TripoSR but not required (can use CPU)
        
        return True

    @classmethod
    def setup_logging(cls) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # httpx 로깅 수준 조정 (heartbeat 404 메시지 억제)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get application cache directory."""
        cache_dir = Path.home() / ".aiweb_clicker_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    @classmethod
    def get_output_dir(cls) -> Path:
        """Get application output directory."""
        output_dir = Path.home() / ".aiweb_clicker_output"
        output_dir.mkdir(exist_ok=True)
        return output_dir
