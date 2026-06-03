"""
Image-to-Goods: AI-Driven Custom Clicker Keyring Generator
Gradio Web Interface (Fixed for TripoSR Serverless Integration)
"""

import logging
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import gradio as gr
from PIL import Image
import requests
from pathlib import Path
import trimesh
import numpy as np
from typing import Optional

from .api import OpenAIImageGenerator, TripoSRModel
from .utils import AppConfig, MeshProcessor
from .ui import create_ui

# Configure logging
AppConfig.setup_logging()
logger = logging.getLogger(__name__)

class ImageToGoodsApp:
    """Gradio-based application for Image-to-Goods."""

    ORIENTATION_PRESETS = {
        "정면": 0.0,
        "정면 우측 45도": 45.0,
        "오른쪽": 90.0,
        "후면": 180.0,
        "왼쪽 뒤 225도": 225.0,
        "왼쪽": 270.0,
    }
    ORIENTATION_AXES = ["Z축(윗면 기준)", "Y축(옆면 기준)"]
    XY_ALIGNMENT_MODES = ["bottom_face", "centroid", "bounding_box_center"]

    UPRIGHT_TARGET_AXES = ["Z축(기본)", "Y축", "X축"]
    # 기본 프리셋: 후면(캐릭터가 사용자 쪽을 바라보도록 설정)
    DEFAULT_ORIENTATION_PRESET = "후면"
    DEFAULT_ORIENTATION_AXIS = "Y축(옆면 기준)"
    # Align the model with the keycap's visual center by default.
    DEFAULT_XY_ALIGNMENT_MODE = "bounding_box_center"

    DEFAULT_UPRIGHT_TARGET_AXIS = "X축"
    def __init__(self):
        """Initialize application state."""
        self.generated_image = None
        self.mesh_bytes = None  # TripoSR이 반환하는 raw bytes 저장을 위해 변경
        self.mesh_format = "glb"
        self.mesh_height = None  # Store mesh height for slider range
        self.preview_image = None
        self.solidified_mesh = None
        self.merged_mesh = None
        self.top_mesh = None
        self.bottom_mesh = None
        self.top_glb_path = None
        self.bottom_glb_path = None
        self.merged_glb_path = None
        self.merged_preview_glb_path = None

    def _apply_upright_rotation(self, mesh: trimesh.Trimesh, target_axis: str, context: str = "") -> Optional[str]:
        if mesh is None:
            return None

        target_axis = target_axis or self.DEFAULT_UPRIGHT_TARGET_AXIS
        axis_map = {
            "X축": "X",
            "Y축": "Y",
            "Z축(기본)": "Z",
        }
        target = axis_map.get(target_axis, "Z")

        bounds = mesh.bounds
        sizes = {
            "X": bounds[1, 0] - bounds[0, 0],
            "Y": bounds[1, 1] - bounds[0, 1],
            "Z": bounds[1, 2] - bounds[0, 2],
        }
        largest_axis = max(sizes.items(), key=lambda x: x[1])[0]
        if largest_axis == target:
            return f"largest axis {largest_axis} already aligned to {target}"

        if largest_axis == "X" and target == "Z":
            rotation_axis = [0, 1, 0]
            angle = np.pi / 2
        elif largest_axis == "Y" and target == "Z":
            rotation_axis = [1, 0, 0]
            angle = np.pi / 2
        elif largest_axis == "Z" and target == "X":
            rotation_axis = [0, 1, 0]
            angle = -np.pi / 2
        elif largest_axis == "Z" and target == "Y":
            rotation_axis = [1, 0, 0]
            angle = -np.pi / 2
        elif largest_axis == "X" and target == "Y":
            rotation_axis = [0, 0, 1]
            angle = np.pi / 2
        elif largest_axis == "Y" and target == "X":
            rotation_axis = [0, 0, 1]
            angle = -np.pi / 2
        else:
            return f"no supported rotation from {largest_axis} to {target}"

        center = (bounds[0] + bounds[1]) / 2.0
        rot = trimesh.transformations.rotation_matrix(angle, rotation_axis, point=center)
        mesh.apply_transform(rot)
        return f"largest axis {largest_axis} -> rotate to {target}"

    def generate_image_openai(self, concept: str) -> tuple:
        """
        Generate side-profile image using OpenAI DALL-E 3 (via gpt-image-2 direct call).

        Args:
            concept: User's concept description

        Returns:
            Tuple of (image, status_message)
        """
        if not concept:
            return None, "❌ 개념을 입력해주세요"

        try:
            generator = OpenAIImageGenerator(api_key=AppConfig.OPENAI_API_KEY)
            logger.info(f"Generating image for: {concept}")

            image = generator.generate_side_profile_image(concept=concept)

            if image:
                self.generated_image = image
                return image, "✅ 이미지 생성 완료!"
            else:
                return None, "❌ 이미지 생성 실패"

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None, f"❌ 오류: {str(e)}"

    def upload_custom_image(self, image_file) -> tuple:
        """
        Handle custom image upload.

        Args:
            image_file: Uploaded image file

        Returns:
            Tuple of (image, status_message)
        """
        try:
            if image_file is None:
                return None, "❌ 이미지를 업로드해주세요"

            image = Image.open(image_file)
            self.generated_image = image
            return image, "✅ 이미지 업로드 완료!"

        except Exception as e:
            logger.error(f"Image upload error: {e}")
            return None, f"❌ 오류: {str(e)}"

    def load_sample_image(self, url: str) -> tuple:
        """Download a sample image from `url` and set it as the current generated image."""
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
            # Convert to RGB for downstream consistency
            if image.mode != "RGB":
                image = image.convert("RGB")
            self.generated_image = image
            return image, "✅ 샘플 이미지 로드 완료"
        except Exception as e:
            logger.error(f"Sample image load error: {e}")
            return None, f"❌ 샘플 이미지 불러오기 실패: {e}"

    def ensure_sample_assets(self) -> list:
        """Ensure sample assets directory exists and return list of existing sample files.

        This function no longer creates placeholder images. Samples must come from
        user-saved images (via `save_current_image_as_sample`).
        """
        try:
            base = Path(__file__).resolve().parent
            samples_dir = base / "assets" / "samples"
            samples_dir.mkdir(parents=True, exist_ok=True)

            # Find image files in the samples directory (png/jpg/jpeg)
            files = sorted(samples_dir.glob("*.png")) + sorted(samples_dir.glob("*.jpg")) + sorted(samples_dir.glob("*.jpeg"))
            return [str(p) for p in files]
        except Exception as e:
            logger.error(f"ensure_sample_assets error: {e}")
            return []

    def load_sample_image_local(self, path: str) -> tuple:
        """Load a local sample image by filesystem path."""
        try:
            p = Path(path)
            if not p.exists():
                return None, f"❌ 파일 없음: {path}"
            image = Image.open(p)
            if image.mode != "RGB":
                image = image.convert("RGB")
            self.generated_image = image
            return image, "✅ 샘플 이미지 로드 완료"
        except Exception as e:
            logger.error(f"Local sample load error: {e}")
            return None, f"❌ 샘플 이미지 불러오기 실패: {e}"

    def download_current_image(self) -> Optional[str]:
        """Export the current generated/uploaded image to a temporary PNG file."""
        try:
            if self.generated_image is None:
                return None
            tmp_path = tempfile.NamedTemporaryFile(suffix="_current.png", delete=False).name
            image = self.generated_image
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(tmp_path)
            return tmp_path
        except Exception as e:
            logger.error(f"download_current_image error: {e}")
            return None


    def get_sample_list(self, max_slots: int = 6) -> tuple:
        """Return up to `max_slots` sample file paths (or None) for UI thumbnails plus a status message."""
        try:
            files = self.ensure_sample_assets()
            files = list(files[:max_slots])
            # pad to max_slots with None
            while len(files) < max_slots:
                files.append(None)
            return files, "✅ 샘플 목록 갱신 완료"
        except Exception as e:
            logger.error(f"get_sample_list error: {e}")
            return [None] * max_slots, f"❌ 샘플 목록 불러오기 실패: {e}"

    def generate_3d_mesh(
        self,
        remove_background: bool = True,
        foreground_ratio: float = 0.85,
        marching_cubes_resolution: int = 256,
        target_height_mm: float = 100.0
    ) -> tuple:
        """
        Generate 3D mesh using TripoSR via Gradio Client.

        Args:
            remove_background: Remove background from image
            foreground_ratio: Ratio of foreground (0.5-1.0)
            marching_cubes_resolution: Mesh resolution (32-320)
            target_height_mm: Target mesh height in mm

        Returns:
            Tuple of (status_message, mesh_glb_path)
        """
        if self.generated_image is None:
            return "❌ 먼저 이미지를 생성하거나 업로드해주세요", None

        try:
            logger.info(f"Generating 3D mesh with parameters:")
            logger.info(f"  remove_background={remove_background}")
            logger.info(f"  foreground_ratio={foreground_ratio}")
            logger.info(f"  marching_cubes_resolution={marching_cubes_resolution}")
            logger.info(f"  target_height_mm={target_height_mm}")

            mesh_gen = TripoSRModel()
            # Pass all parameters to TripoSR
            mesh_result = mesh_gen.generate_3d_mesh(
                image=self.generated_image,
                remove_background=remove_background,
                foreground_ratio=foreground_ratio,
                marching_cubes_resolution=marching_cubes_resolution
            )

            if mesh_result and mesh_result.get("success"):
                # TripoSR의 결과 메시 파일 경로 저장
                self.mesh_bytes = mesh_result.get("mesh_data")
                mesh_obj = mesh_result.get("mesh_data_obj")
                mesh_format = mesh_result.get("format", "glb")
                self.mesh_format = mesh_format
                self.merged_mesh = None
                self.merged_glb_path = None
                self.top_mesh = None
                self.bottom_mesh = None
                self.top_glb_path = None
                self.bottom_glb_path = None
                
                try:
                    from pathlib import Path
                    # MeshProcessor imported from utils above
                    mesh_size = 0
                    if isinstance(self.mesh_bytes, str) and Path(self.mesh_bytes).exists():
                        mesh_size = Path(self.mesh_bytes).stat().st_size / (1024 * 1024)
                    
                    # Load mesh temporarily to get bounds and apply target height scaling
                    temp_processor = MeshProcessor(
                        mesh_data=self.mesh_bytes,
                        format=mesh_format,
                        preserve_orientation=True,
                    )
                    
                    # Apply custom target height scaling
                    bounds = temp_processor.mesh.bounds
                    current_height = bounds[1, 2] - bounds[0, 2]
                    
                    if current_height > 0 and current_height != target_height_mm:
                        # Scale to target height
                        scale_factor = target_height_mm / current_height
                        temp_processor.mesh.apply_scale(scale_factor)
                        logger.info(f"Scaled mesh from {current_height:.2f}mm to {target_height_mm:.2f}mm (factor: {scale_factor:.2f}x)")
                        
                        # Re-export scaled mesh
                        if isinstance(self.mesh_bytes, str):
                            temp_processor.mesh.export(self.mesh_bytes, file_type=mesh_format)
                    
                    # Get final bounds
                    final_bounds = temp_processor.mesh.bounds
                    final_height = final_bounds[1, 2] - final_bounds[0, 2]
                    
                    status_msg = (
                        f"✅ 3D 메시 생성 완료!\n"
                        f"형식: {mesh_format.upper()}\n"
                        f"크기: {mesh_size:.2f}MB\n"
                        f"메시 높이: {final_height:.1f}mm\n"
                        f"해상도: {marching_cubes_resolution}"
                    )
                    
                    # Store mesh height for slider update
                    self.mesh_height = final_height

                    # 🌟 [핵심 변경] 그래프(fig) 객체 대신, GLB 파일 경로(self.mesh_bytes)를 반환하도록 수정
                    return status_msg, self.mesh_bytes
                    
                except Exception as e:
                    logger.warning(f"Could not get mesh bounds: {e}")
                    self.preview_image = None
                    return f"✅ 3D 메시 생성 완료!\n형식: {mesh_format.upper()}\n크기: {mesh_size:.2f}MB", self.mesh_bytes
            else:
                # If upstream provided an error message, forward it to the UI
                try:
                    if isinstance(mesh_result, dict) and mesh_result.get("error"):
                        return f"❌ 3D 메시 생성 실패: {mesh_result.get('error')}", None
                except Exception:
                    pass
                return "❌ 3D 메시 생성 실패", None

        except Exception as e:
            logger.error(f"Mesh generation error: {e}")
            return f"❌ 오류: {str(e)}", None


    def _build_axis_rotation(self, mesh: trimesh.Trimesh, angle_deg: float, axis_key: str) -> Optional[np.ndarray]:
        axis = {
            "Z축(윗면 기준)": [0, 0, 1],
            "Y축(옆면 기준)": [0, 1, 0],
        }.get(axis_key)
        if axis is None or mesh is None:
            return None
        bounds = mesh.bounds
        center = (bounds[0] + bounds[1]) / 2.0
        return trimesh.transformations.rotation_matrix(np.deg2rad(float(angle_deg)), axis, point=center)


    def merge_solid_mesh_with_base_keycap(
        self,
        merge_pitch_mm: float,
        orientation_preset: str,
        orientation_axis: str,
        upright_target_axis: str,
        xy_alignment_mode: str,
    ) -> tuple:
        """Solidify the generated model and merge it with the configured base keycap."""
        if self.mesh_bytes is None:
            return None, "❌ 먼저 3D 메시를 생성해주세요"

        base_source = AppConfig.BASE_KEYCAP_MODEL_SOURCE.strip()
        if not base_source:
            return None, (
                "❌ BASE_KEYCAP_MODEL_SOURCE가 설정되지 않았습니다.\n"
                "예: .env에 로컬 GLB 경로나 https URL을 넣어주세요"
            )

        try:
            orientation_yaw_deg = float(self.ORIENTATION_PRESETS.get(orientation_preset, 0.0))

            processor = MeshProcessor(
                mesh_data=self.mesh_bytes,
                format=self.mesh_format,
                preserve_orientation=True,
            )
            # Reuse preview solid if available to avoid expensive re-solidify
            existing_solid = None
            existing_solid_info = None
            if hasattr(self, 'last_preview_solid') and self.last_preview_solid is not None:
                existing_solid = self.last_preview_solid
                existing_solid_info = getattr(self, 'last_preview_solid_info', None)

            merged_mesh, debug_info = processor.merge_solid_mesh_with_base_cap(
                base_mesh_source=base_source,
                base_format="glb",
                pitch_mm=merge_pitch_mm,
                overlap_mm=0.35,
                fit_ratio=0.82,
                orientation_yaw_deg=orientation_yaw_deg,
                orientation_axis=orientation_axis,
                upright_target_axis=upright_target_axis,
                existing_solid_mesh=existing_solid,
                existing_solid_info=existing_solid_info,
                xy_alignment_mode=xy_alignment_mode,
            )

            if merged_mesh is None:
                return None, "❌ 기본 상부와 합치기에 실패했습니다"

            self.merged_mesh = merged_mesh
            merged_glb = tempfile.NamedTemporaryFile(suffix="_merged.glb", delete=False).name
            merged_mesh.export(merged_glb)
            self.merged_glb_path = merged_glb
            self.merged_preview_glb_path = debug_info.get("preview_glb_path")

            status_msg = "✅ 기본 상부와 합치기 완료!"

            return self.merged_preview_glb_path or merged_glb, status_msg

        except Exception as e:
            logger.error(f"Keycap union error: {e}")
            return None, f"❌ 오류: {str(e)}"

    def download_glb_original(self) -> Optional[str]:
        """Download original mesh as GLB file path."""
        if self.mesh_bytes is None:
            return None
        try:
            if isinstance(self.mesh_bytes, str):
                # Already a file path
                return self.mesh_bytes
            else:
                # Save bytes to temporary file
                tmp_path = tempfile.NamedTemporaryFile(suffix="_original.glb", delete=False).name
                with open(tmp_path, 'wb') as f:
                    f.write(self.mesh_bytes)
                return tmp_path
        except Exception as e:
            logger.error(f"Error preparing GLB download: {e}")
            return None

    def download_obj_original(self) -> Optional[str]:
        """Download original mesh as OBJ file path."""
        if self.mesh_bytes is None:
            return None
        try:
            processor = MeshProcessor(
                mesh_data=self.mesh_bytes,
                format=getattr(self, "mesh_format", "glb"),
                preserve_orientation=True,
            )
            tmp_path = tempfile.NamedTemporaryFile(suffix="_original.obj", delete=False).name
            processor.mesh.export(tmp_path, file_type="obj")
            return tmp_path
        except Exception as e:
            logger.error(f"Error exporting original mesh as OBJ: {e}")
            return None

    def download_final_glb(self) -> Optional[str]:
        """Download the final mesh as a GLB file path."""
        if self.merged_glb_path is not None:
            return self.merged_glb_path
        return self.download_glb_original()

    def download_final_obj(self) -> Optional[str]:
        """Download the final merged mesh as an OBJ file path."""
        try:
            if self.merged_mesh is None:
                # fallback to original mesh converted to OBJ
                return self.download_obj_original()

            tmp_path = tempfile.NamedTemporaryFile(suffix="_merged.obj", delete=False).name
            # export requires file_type override for OBJ
            self.merged_mesh.export(tmp_path, file_type="obj")
            return tmp_path
        except Exception as e:
            logger.error(f"Error exporting merged mesh as OBJ: {e}")
            return None

    def download_stl_bottom(self):
        """
        키링용 하단부 고정 파일(base_keycap2.stl)을 다운로드하도록 경로를 반환합니다.
        """
        from pathlib import Path
        
        # 프로젝트 최상단 디렉토리 또는 현재 파일 위치를 기준으로 assets 경로를 잡습니다.
        # (프로젝트 구조에 따라 부모 디렉토리 .parent 호출 횟수를 조절해 주세요)
        base_dir = Path(__file__).resolve().parent
        file_path = base_dir / "assets" / "base_keycap2.stl"
        
        if file_path.exists():
            # 파일이 존재하면 해당 경로를 문자열로 반환하여 Gradio 다운로드 버튼에 넘겨줌
            return str(file_path)
        else:
            # 파일이 없을 경우 콘솔에 에러를 띄우고 None 반환
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
            return None



def main():
    """Main application entry point."""

    # Validate configuration via AppConfig
    try:
        # 시스템에 매핑된 환경 변수 키 자동 검증
        AppConfig.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Initialize app
    app = ImageToGoodsApp()

    try:
        import scipy  # noqa: F401
        scipy_status = "available"
    except Exception as e:
        scipy_status = f"missing ({e})"

    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"SciPy status: {scipy_status}")

    # Create and launch UI
    interface = create_ui(app)
    print("\nGradio server starting")
    print("Open in browser: http://localhost:7860")
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        allowed_paths=["."]
    )


if __name__ == "__main__":
    main()