"""
Application Configuration Management
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class AppConfig:
    """Application configuration from environment variables."""

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # 선택: IMAGE_TO_3D_BACKEND=triposr 일 때만 사용 (Space GPU 쿼터가 늘어난다)
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")

    # 이미지→3D 백엔드: "lowpoly"(기본, 내 PC에서 실행, GPU/네트워크 불필요) | "triposr"(HF Space 호출)
    IMAGE_TO_3D_BACKEND: str = os.getenv("IMAGE_TO_3D_BACKEND", "lowpoly").strip().lower()
    # triposr 백엔드가 호출할 Gradio Space (예: "kingy0ujin/TripoSR")
    TRIPOSR_SPACE_URL: str = os.getenv("TRIPOSR_SPACE_URL", "stabilityai/TripoSR")

    # Application Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 키캡 하부와 결합하는 방식: "auto"(기본: 닫힌 입체면 직접 결합, 아니면 복셀) | "direct" | "voxel"
    MERGE_MODE: str = os.getenv("MERGE_MODE", "auto").strip().lower()
    BASE_KEYCAP_MODEL_SOURCE: str = os.getenv(
        "BASE_KEYCAP_MODEL_SOURCE",
        str(Path(__file__).resolve().parents[1] / "assets" / "base_keycap.stl")
    )

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
