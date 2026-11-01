"""
Gradio Client TripoSR Integration (선택 백엔드: IMAGE_TO_3D_BACKEND=triposr)
Generates 3D mesh (.obj/.glb) from a single image using Gradio client to call TripoSR Gradio Space

gradio-client 가 필요하다. 기본 백엔드(lowpoly)에서는 이 모듈을 불러오지 않는다.
"""

import time
import logging
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from gradio_client import Client, file as gradio_file
from gradio_client import exceptions as gradio_errors

from ..utils.config import AppConfig

logger = logging.getLogger(__name__)


class TripoSRModel:
    """
    TripoSR Integration via Gradio Client
    Calls TripoSR Gradio Space to generate 3D mesh from a single image

        TripoSR API Flow:
        1. /preprocess - 이미지 전처리 (배경 제거 옵션)
        2. /generate - 3D 메시 생성 (OBJ, GLB 반환)
    """

    # TripoSR Gradio Space (환경변수 TRIPOSR_SPACE_URL로 변경 가능)
    TRIPOSR_SPACE_URL = AppConfig.TRIPOSR_SPACE_URL

    RETRY_COUNT = 3
    RETRY_BACKOFF_S = 10

    def __init__(self):
        """
        Initialize Gradio Client for TripoSR.
        """
        self.client = None
        self.init_error: Optional[str] = None
        logger.info("Initializing TripoSR Gradio Client")
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize the Gradio Client connection to TripoSR Space.

        Note: The heartbeat 404 error is harmless and occurs during connection.
        연결 실패 시 예외를 던지지 않고 init_error에 원인을 저장한다.
        """
        try:
            logger.info(f"Connecting to TripoSR Space: {self.TRIPOSR_SPACE_URL}")
            kwargs = {}
            if AppConfig.HF_API_TOKEN:
                # 토큰이 있으면 GPU 쿼터가 늘어나고 private Space에도 접근 가능
                kwargs["hf_token"] = AppConfig.HF_API_TOKEN
            self.client = Client(self.TRIPOSR_SPACE_URL, **kwargs)
            logger.info("✓ TripoSR Gradio Client initialized successfully")
        except Exception as e:
            self.init_error = f"{type(e).__name__}: {e}"
            logger.error(f"Failed to initialize Gradio Client: {self.init_error}")
            traceback.print_exc()

    def _predict_with_retries(self, *args, api_name: Optional[str] = None):
        """
        client.predict 호출. GPU 부족/큐 문제 등 일시적 오류는 대기 후 재시도한다.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.RETRY_COUNT + 1):
            try:
                return self.client.predict(*args, api_name=api_name)
            except Exception as e:
                last_exc = e
                msg = str(e)
                lowered = msg.lower()
                transient = (
                    isinstance(e, gradio_errors.AppError)
                    or "no gpu" in lowered
                    or "quota" in lowered
                    or "queue" in lowered
                    or "timeout" in lowered
                    or "503" in lowered
                )
                logger.warning(
                    f"{api_name} failed (attempt {attempt}/{self.RETRY_COUNT}): "
                    f"{type(e).__name__}: {msg}"
                )
                # GPU 쿼터 초과는 대기해도 풀리지 않는 경우가 많아 바로 중단
                if "exceeded your" in lowered and "quota" in lowered:
                    raise
                if transient and attempt < self.RETRY_COUNT:
                    sleep_time = self.RETRY_BACKOFF_S * attempt
                    logger.info(f"Waiting {sleep_time}s before retrying...")
                    time.sleep(sleep_time)
                    continue
                raise
        raise last_exc  # pragma: no cover

    def _validate_and_prepare_image(self, image: Image.Image) -> tuple[Path, Image.Image]:
        """
        Validate and prepare image for TripoSR processing.

        Args:
            image: PIL Image object

        Returns:
            Tuple of (file_path, prepared_image)
        """
        # Convert RGBA to RGB if necessary
        if image.mode == 'RGBA':
            logger.info("Converting RGBA image to RGB")
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != 'RGB':
            logger.info(f"Converting {image.mode} image to RGB")
            image = image.convert('RGB')

        logger.info(f"Image size: {image.size}")

        # 동시 요청/파일 잠금 충돌을 피하기 위해 요청마다 고유 파일명 사용
        temp_dir = Path(tempfile.gettempdir()) / "triposr_input"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_image_path = temp_dir / f"input_{uuid.uuid4().hex}.png"
        image.save(temp_image_path, format='PNG')
        logger.info(f"Image saved to: {temp_image_path}")

        return temp_image_path, image

    @staticmethod
    def _fail(message: str) -> Dict[str, Any]:
        """UI에 원인을 전달하기 위한 실패 결과."""
        return {"success": False, "error": message}

    def generate_3d_mesh(
        self,
        image: Image.Image,
        remove_background: bool = True,
        foreground_ratio: float = 0.85,
        marching_cubes_resolution: int = 256
    ) -> Optional[Dict[str, Any]]:
        """
        Generate 3D mesh from input PIL image using TripoSR Gradio Space via Gradio Client.

        Args:
            image: PIL Image object (input image)
            remove_background: Whether to remove background from image
            foreground_ratio: Ratio of foreground to image size (0.5-1.0)
            marching_cubes_resolution: Resolution for mesh generation (32-320)

        Returns:
            Dictionary with mesh data path and metadata on success
            ({"success": True, ...}), or {"success": False, "error": str} on failure.
        """
        if self.client is None:
            logger.error("Gradio Client not initialized")
            return self._fail(
                f"TripoSR Space({self.TRIPOSR_SPACE_URL}) 연결 실패: {self.init_error}"
            )

        try:
            logger.info("Generating 3D mesh using TripoSR...")

            # Step 1: Validate and prepare image
            logger.info("Step 1: Validating and preparing image...")
            try:
                temp_image_path, _ = self._validate_and_prepare_image(image)
            except Exception as e:
                logger.error(f"Image preparation failed: {e}")
                return self._fail(f"이미지 준비 실패: {e}")

            # Step 2: Preprocess image
            logger.info("Step 2: Preprocessing image...")
            try:
                preprocessed_image = self._predict_with_retries(
                    gradio_file(str(temp_image_path)),
                    remove_background,
                    foreground_ratio,
                    api_name="/preprocess",
                )
                logger.info(f"✓ Preprocessed image path: {preprocessed_image}")
            except Exception as e:
                logger.error(f"Preprocessing failed: {e}")
                traceback.print_exc()
                return self._fail(f"전처리(/preprocess) 실패: {type(e).__name__}: {e}")

            # Step 3: Generate 3D mesh
            logger.info("Step 3: Generating 3D mesh...")
            try:
                result = self._predict_with_retries(
                    gradio_file(preprocessed_image),
                    marching_cubes_resolution,
                    api_name="/generate",
                )
                logger.info("✓ 3D mesh generated successfully")
            except Exception as e:
                logger.error(f"Mesh generation failed: {e}")
                traceback.print_exc()
                return self._fail(f"메시 생성(/generate) 실패: {type(e).__name__}: {e}")

            # Step 4: Handle result (tuple of obj_path, glb_path)
            if isinstance(result, (tuple, list)) and len(result) >= 2:
                obj_path = result[0]
                glb_path = result[1]

                logger.info(f"✓ OBJ output: {obj_path}")
                logger.info(f"✓ GLB output: {glb_path}")

                return {
                    "mesh_data": glb_path,
                    "mesh_data_obj": obj_path,
                    "format": "glb",
                    "success": True
                }

            logger.error(f"Unexpected result format: {result}")
            return self._fail(f"예상하지 못한 응답 형식: {result}")

        except Exception as e:
            logger.error(f"Error during TripoSR inference: {e}")
            traceback.print_exc()
            return self._fail(f"{type(e).__name__}: {e}")



