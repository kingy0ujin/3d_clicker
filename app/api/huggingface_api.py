"""
Gradio Client TripoSR Integration
Generates 3D mesh (.obj/.glb) from a single image using Gradio client to call TripoSR Gradio Space
"""

import time
import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from gradio_client import Client, file as gradio_file
from gradio_client import exceptions as gradio_errors

logger = logging.getLogger(__name__)


class TripoSRModel:
    """
    TripoSR Integration via Gradio Client
    Calls TripoSR Gradio Space to generate 3D mesh from a single image
    
        TripoSR API Flow:
        1. /preprocess - 이미지 전처리 (배경 제거 옵션)
        2. /generate - 3D 메시 생성 (OBJ, GLB 반환)
    """

    # TripoSR Gradio Space (올바른 URL)
    TRIPOSR_SPACE_URL = "stabilityai/TripoSR"

    def __init__(self):
        """
        Initialize Gradio Client for TripoSR.
        """
        self.client = None
        logger.info("Initializing TripoSR Gradio Client")
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize the Gradio Client connection to TripoSR Space.
        
        Note: The heartbeat 404 error is harmless and occurs during connection.
        The actual predictions work correctly despite this warning.
        """
        try:
            logger.info(f"Connecting to TripoSR Space: {self.TRIPOSR_SPACE_URL}")
            self.client = Client(self.TRIPOSR_SPACE_URL)
            logger.info("✓ TripoSR Gradio Client initialized successfully")
            logger.info("  Actual URL: https://stabilityai-triposr.hf.space")
            logger.info("  Note: Heartbeat 404 errors are expected and harmless")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gradio Client: {e}")
            raise

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
        
        # TripoSR expects images around 512x512 but can handle various sizes
        logger.info(f"Image size: {image.size}")
        
        # Save to temporary file
        temp_dir = Path(tempfile.gettempdir()) / "triposr_input"
        temp_dir.mkdir(exist_ok=True)
        temp_image_path = temp_dir / "input_image.png"
        image.save(temp_image_path, format='PNG')
        logger.info(f"Image saved to: {temp_image_path}")
        
        return temp_image_path, image

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
                    def _predict_with_retries(*args, api_name=None, retries: int = 3, backoff_s: int = 10, **kwargs):
                        last_exc = None
                        for attempt in range(1, retries + 1):
                            try:
                                return self.client.predict(*args, api_name=api_name, **kwargs)
                            except gradio_errors.AppError as ae:
                                last_exc = ae
                                msg = str(ae)
                                logger.warning(f"Upstream AppError (attempt {attempt}/{retries}): {msg}")
                                # If GPU unavailable, wait and retry
                                if "No GPU" in msg or "no gpu" in msg.lower() or "No GPU was available" in msg:
                                    if attempt < retries:
                                        sleep_time = backoff_s * attempt
                                        logger.info(f"GPU unavailable — waiting {sleep_time}s before retrying...")
                                        time.sleep(sleep_time)
                                        continue
                                    else:
                                        raise
                                else:
                                    # Non-GPU AppError — re-raise to be handled by outer logic
                                    raise

            remove_background: Whether to remove background from image
            foreground_ratio: Ratio of foreground to image size (0.5-1.0)
            marching_cubes_resolution: Resolution for mesh generation (32-320)
            
        Returns:
            Dictionary containing mesh data path and metadata, or None if failed.
        """
        if self.client is None:
            logger.error("Gradio Client not initialized")
            return None
            
        try:
            logger.info("Generating 3D mesh using TripoSR...")
            
            # Step 1: Validate and prepare image
            logger.info("Step 1: Validating and preparing image...")
            try:
                temp_image_path, prepared_image = self._validate_and_prepare_image(image)
            except Exception as e:
                logger.error(f"Image preparation failed: {e}")
                return None
            
            # Step 2: Preprocess image using gradio_client.file()
            logger.info("Step 2: Preprocessing image...")
            try:
                # Use gradio_client.file() to explicitly pass file path
                preprocessed_image = self.client.predict(
                    gradio_file(str(temp_image_path)),  # input_image with explicit file()
                    remove_background,                  # remove_background
                    foreground_ratio,                   # foreground_ratio
                    api_name="/preprocess"
                )
                logger.info(f"✓ Image preprocessed successfully")
                logger.info(f"  Preprocessed image path: {preprocessed_image}")
            except Exception as e:
                logger.error(f"Preprocessing failed: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            # Step 3: Generate 3D mesh
            logger.info("Step 3: Generating 3D mesh...")
            try:
                # Use gradio_client.file() for preprocessed image as well
                result = self.client.predict(
                    gradio_file(preprocessed_image),    # processed_image with explicit file()
                    marching_cubes_resolution,          # marching_cubes_resolution
                    api_name="/generate"
                )
                logger.info(f"✓ 3D mesh generated successfully")
            except Exception as e:
                logger.error(f"Mesh generation failed: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            # Step 4: Handle result (tuple of obj_path, glb_path)
            if isinstance(result, (tuple, list)) and len(result) >= 2:
                obj_path = result[0]  # OBJ format
                glb_path = result[1]  # GLB format
                
                logger.info(f"✓ OBJ output: {obj_path}")
                logger.info(f"✓ GLB output: {glb_path}")
                
                # Return GLB format (더 현대적인 형식)
                return {
                    "mesh_data": glb_path,
                    "mesh_data_obj": obj_path,  # OBJ도 함께 저장
                    "format": "glb",
                    "success": True
                }
            else:
                logger.error(f"Unexpected result format: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error during TripoSR inference: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_3d_mesh_raw(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Generate 3D mesh directly from raw image bytes.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return self.generate_3d_mesh(image)
        except Exception as e:
            logger.error(f"Error processing raw image bytes: {e}")
            return None


# Alias for backward compatibility
HuggingFaceTripoSR = TripoSRModel