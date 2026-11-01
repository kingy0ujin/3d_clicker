"""API modules for external service integrations"""

import logging

from .openai_api import OpenAIImageGenerator
from .lowpoly_api import LowPolyModel
from ..utils.config import AppConfig

logger = logging.getLogger(__name__)


def create_mesh_generator():
    """
    AppConfig.IMAGE_TO_3D_BACKEND 설정에 따라 이미지→3D 생성기를 만든다.
    - "lowpoly" (기본): 내 PC에서 실루엣 기반 로우폴리 생성 (GPU/네트워크 불필요)
    - "triposr": TRIPOSR_SPACE_URL 의 TripoSR Gradio Space 호출 (gradio-client 필요)
    """
    backend = AppConfig.IMAGE_TO_3D_BACKEND
    if backend == "triposr":
        # gradio_client 는 이 백엔드에서만 필요하므로 여기서 불러온다
        from .huggingface_api import TripoSRModel

        logger.info("Image-to-3D backend: TripoSR")
        return TripoSRModel()
    if backend != "lowpoly":
        logger.warning(f"Unknown IMAGE_TO_3D_BACKEND '{backend}', falling back to lowpoly")
    logger.info("Image-to-3D backend: local Low-Poly")
    return LowPolyModel()


__all__ = ["OpenAIImageGenerator", "LowPolyModel", "create_mesh_generator"]
