"""
Trimesh-based Mesh Processing and Auto-Slicing
Splits 3D mesh into top (keycap) and bottom (housing) parts
with mechanical switch fitting (14mm x 14mm + cross slot)
"""

import io
import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional, List, Union
from urllib.parse import urlparse
from urllib.request import urlopen

import numpy as np
import trimesh
from trimesh import Trimesh
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)



class MeshProcessor:
    """
    Processes 3D meshes to prepare them for mechanical assembly:
    - Auto-slicing at specified height
    - Boolean operations for switch cavity
    - Structural validation
    """

    def __init__(self, mesh_data: Union[bytes, str], format: str = "obj", preserve_orientation: bool = False):
        """
        Initialize mesh processor.
        
        Args:
            mesh_data: Raw mesh data (bytes) or file path (str)
            format: Mesh format ("obj", "stl", "glb", "ply")
        """
        self.raw_data = mesh_data
        self.format = format
        # If True, do not auto-rotate loaded meshes to align largest axis to Z.
        # Useful when we want to preserve the original orientation from the
        # generation pipeline and position it on top of the base model as-is.
        self.preserve_orientation = bool(preserve_orientation)
        self.mesh: Optional[Trimesh] = None
        self.top_mesh: Optional[Trimesh] = None
        self.bottom_mesh: Optional[Trimesh] = None
        
        self._load_mesh()

    def _load_mesh(self) -> None:
        """Load mesh from raw data or file path using Trimesh."""
        try:
            loaded = self._load_mesh_from_source(self.raw_data, self.format)
            
            # Handle Scene objects (GLB/GLTF often returns Scene)
            if isinstance(loaded, trimesh.Scene):
                logger.info("Loaded object is a Scene, extracting geometry...")
                # Convert Scene to Mesh by dumping all geometry
                self.mesh = loaded.dump(concatenate=True)
                if self.mesh is None:
                    # If dump returns None, try to get first geometry
                    geometries = list(loaded.geometry.values())
                    if geometries:
                        self.mesh = geometries[0]
                    else:
                        raise ValueError("Scene has no geometry")
            else:
                # Already a Mesh
                self.mesh = loaded
            
            # Validate and repair mesh if needed
            logger.info(f"Mesh loaded: {len(self.mesh.vertices)} vertices, "
                       f"{len(self.mesh.faces)} faces")
            
            # Try to validate and repair
            try:
                if hasattr(self.mesh, 'remove_degenerate_faces'):
                    self.mesh.remove_degenerate_faces()
                if hasattr(self.mesh, 'remove_infinite_values'):
                    self.mesh.remove_infinite_values()
                logger.info("Mesh validation and repair completed")
            except Exception as e:
                logger.warning(f"Mesh validation failed: {e}")
            
            # Auto-scale and orient mesh
            # TripoSR often returns meshes in normalized coordinates
            bounds = self.mesh.bounds
            mesh_x_size = bounds[1, 0] - bounds[0, 0]
            mesh_y_size = bounds[1, 1] - bounds[0, 1]
            mesh_z_size = bounds[1, 2] - bounds[0, 2]
            
            logger.info(f"Original mesh bounds: X={mesh_x_size:.4f}, Y={mesh_y_size:.4f}, Z={mesh_z_size:.4f}")
            
            # Find which axis is the largest (should be the height)
            sizes = {'X': mesh_x_size, 'Y': mesh_y_size, 'Z': mesh_z_size}
            sorted_sizes = sorted(sizes.items(), key=lambda x: x[1], reverse=True)
            largest_axis = sorted_sizes[0][0]
            largest_size = sorted_sizes[0][1]

            logger.info(f"Largest dimension: {largest_axis} axis ({largest_size:.4f}mm)")

            # Optionally rotate mesh so largest axis becomes Z. This behavior
            # preserves previous behavior by default, but can be disabled by
            # passing preserve_orientation=True to the constructor.
            if not getattr(self, "preserve_orientation", False):
                if largest_axis != 'Z':
                    logger.warning(f"Mesh orientation issue: largest dimension is {largest_axis}, not Z. Rotating mesh...")
                    if largest_axis == 'X':
                        # Rotate 90 degrees around Y axis (X -> Z)
                        rotation_matrix = trimesh.transformations.rotation_matrix(
                            angle=np.pi/2,
                            direction=[0, 1, 0]
                        )
                    elif largest_axis == 'Y':
                        # Rotate 90 degrees around X axis (Y -> Z)
                        rotation_matrix = trimesh.transformations.rotation_matrix(
                            angle=np.pi/2,
                            direction=[1, 0, 0]
                        )

                    self.mesh.apply_transform(rotation_matrix)
                    bounds = self.mesh.bounds
                    logger.info(f"After rotation: X={bounds[1, 0] - bounds[0, 0]:.4f}, Y={bounds[1, 1] - bounds[0, 1]:.4f}, Z={bounds[1, 2] - bounds[0, 2]:.4f}")
            else:
                logger.info("Preserving original mesh orientation (no auto-rotate)")
            
            # Recalculate after potential rotation
            mesh_z_size = bounds[1, 2] - bounds[0, 2]
            
            # If mesh is very small (< 1mm), scale it up
            # Assume normalized coordinates and scale to ~100mm height
            if mesh_z_size < 1.0:
                scale_factor = 100.0 / mesh_z_size
                logger.info(f"Mesh is very small ({mesh_z_size:.4f}mm). Scaling by {scale_factor:.1f}x to ~100mm height")
                self.mesh.apply_scale(scale_factor)
                
                # Update bounds after scaling
                bounds = self.mesh.bounds
                mesh_height = bounds[1, 2] - bounds[0, 2]
                mesh_width = bounds[1, 0] - bounds[0, 0]
                mesh_depth = bounds[1, 1] - bounds[0, 1]
                logger.info(f"Scaled mesh bounds: width={mesh_width:.1f}mm, depth={mesh_depth:.1f}mm, height={mesh_height:.1f}mm")
            
        except Exception as e:
            logger.error(f"Error loading mesh: {e}")
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def _load_mesh_from_source(mesh_source: Union[bytes, str], file_format: str = "glb") -> Trimesh:
        """Load a Trimesh from bytes, local path, or URL.

        The helper also accepts Scene objects and converts them to a single mesh.
        """
        if isinstance(mesh_source, bytes):
            file_obj = io.BytesIO(mesh_source)
            loaded = trimesh.load(file_obj, file_type=file_format, process=True)
        elif isinstance(mesh_source, str):
            parsed = urlparse(mesh_source)
            if parsed.scheme in {"http", "https"}:
                with urlopen(mesh_source) as response:
                    file_obj = io.BytesIO(response.read())
                    loaded = trimesh.load(file_obj, file_type=file_format, process=True)
            else:
                if not Path(mesh_source).exists():
                    raise FileNotFoundError(f"Mesh file not found: {mesh_source}")
                loaded = trimesh.load(mesh_source, file_type=file_format, process=True)
        else:
            raise TypeError(f"Unsupported mesh source type: {type(mesh_source)}")

        if isinstance(loaded, trimesh.Scene):
            logger.info("Loaded object is a Scene, extracting geometry...")
            loaded_mesh = loaded.dump(concatenate=True)
            if loaded_mesh is None:
                geometries = list(loaded.geometry.values())
                if geometries:
                    loaded_mesh = geometries[0]
                else:
                    raise ValueError("Scene has no geometry")
            loaded = loaded_mesh

        if not isinstance(loaded, Trimesh):
            raise TypeError(f"Loaded object is not a Trimesh: {type(loaded)}")

        return loaded

    def solidify_with_voxels(self, pitch_mm: Optional[float] = None, fill_holes: bool = True) -> Tuple[Trimesh, dict]:
        """Fill the mesh interior with voxels and rebuild a watertight outer shell.

        Args:
            pitch_mm: Voxel size in millimeters. Smaller values preserve more detail
                but increase memory and runtime. If omitted, a value is chosen from
                the mesh size.
            fill_holes: Whether to fill enclosed voxel cavities before surface rebuild.

        Returns:
            Tuple of (solid_mesh, debug_info)
        """
        if self.mesh is None:
            raise ValueError("Mesh not loaded")

        debug_info = {
            "success": False,
            "pitch_mm": pitch_mm,
            "fill_holes": fill_holes,
            "original_vertices": len(self.mesh.vertices),
            "original_faces": len(self.mesh.faces),
            "original_volume": float(self.mesh.volume),
        }

        mesh = self.mesh.copy()

        try:
            bounds = mesh.bounds
            size = bounds[1] - bounds[0]
            largest_dim = float(np.max(size))

            if pitch_mm is None:
                # Balance fidelity and runtime: around 120 voxels across the largest axis.
                pitch_mm = max(largest_dim / 120.0, 0.25)

            if pitch_mm <= 0:
                raise ValueError("pitch_mm must be positive")

            debug_info["pitch_mm"] = float(pitch_mm)

            voxel_grid = None
            try:
                from trimesh.voxel.creation import voxelize
                voxel_grid = voxelize(mesh, pitch=pitch_mm)
            except Exception:
                voxel_grid = mesh.voxelized(pitch_mm)

            if voxel_grid is None:
                raise RuntimeError("Voxelization returned no grid")

            if fill_holes:
                try:
                    filled_grid = voxel_grid.fill()
                except Exception:
                    filled_grid = voxel_grid
            else:
                filled_grid = voxel_grid

            try:
                solid_mesh = trimesh.voxel.ops.matrix_to_marching_cubes(
                    filled_grid.matrix,
                    pitch=filled_grid.pitch,
                )
            except Exception:
                try:
                    solid_mesh = filled_grid.marching_cubes
                except Exception:
                    solid_mesh = filled_grid.as_boxes()

            if hasattr(solid_mesh, "geometry"):
                solid_mesh = solid_mesh.dump(concatenate=True)

            if not isinstance(solid_mesh, Trimesh):
                raise RuntimeError(f"Voxel rebuild produced unsupported type: {type(solid_mesh)}")

            try:
                solid_mesh.remove_degenerate_faces()
                solid_mesh.remove_unreferenced_vertices()
                solid_mesh.merge_vertices()
                if hasattr(trimesh, 'repair') and hasattr(trimesh.repair, 'fill_holes'):
                    trimesh.repair.fill_holes(solid_mesh)
            except Exception:
                pass

            debug_info["result_vertices"] = len(solid_mesh.vertices)
            debug_info["result_faces"] = len(solid_mesh.faces)
            debug_info["result_volume"] = float(solid_mesh.volume)
            debug_info["result_is_watertight"] = bool(getattr(solid_mesh, "is_watertight", False))
            debug_info["success"] = True

            return solid_mesh, debug_info

        except Exception as e:
            logger.error(f"Error solidifying mesh with voxels: {e}")
            debug_info["error"] = str(e)
            return mesh, debug_info

  
    def merge_solid_mesh_with_base_cap(
        self,
        base_mesh_source: Union[bytes, str],
        base_format: str = "glb",
        pitch_mm: Optional[float] = None,
        overlap_mm: float = 0.35,
        fit_ratio: float = 0.82,
        orientation_yaw_deg: float = 0.0,
        orientation_axis: Union[str, List[float], Tuple[float, float, float]] = (0, 0, 1),
        upright_target_axis: str = "Z축(기본)",
        existing_solid_mesh: Optional[Trimesh] = None,
        existing_solid_info: Optional[dict] = None,
        xy_alignment_mode: str = "bounding_box_center",
    ) -> Tuple[Trimesh, dict]:
        """Solidify the current mesh and merge it with a base keycap model.

        The method first attempts a boolean union. If that is not available,
        it falls back to voxel-solidifying the aligned assembly so the result is
        still a single watertight mesh.
        """
        if self.mesh is None:
            raise ValueError("Mesh not loaded")

        if existing_solid_mesh is not None:
            solid_mesh = existing_solid_mesh.copy()
            solid_info = existing_solid_info or {}
        else:
            solid_mesh, solid_info = self.solidify_with_voxels(pitch_mm=pitch_mm, fill_holes=True)
        if isinstance(base_mesh_source, str) and base_format == "glb":
            suffix = Path(base_mesh_source.split("?", 1)[0]).suffix.lower()
            if suffix in {".stl", ".obj", ".ply", ".glb", ".gltf"}:
                base_format = suffix.lstrip(".")

        base_mesh = self._load_mesh_from_source(base_mesh_source, base_format)

        base_mesh = base_mesh.copy()
        solid_mesh = solid_mesh.copy() if isinstance(solid_mesh, Trimesh) else self.mesh.copy()

        axis_vector = orientation_axis
        if isinstance(axis_vector, str):
            axis_vector = {
                "Z축(윗면 기준)": (0, 0, 1),
                "Y축(옆면 기준)": (0, 1, 0),
            }.get(axis_vector, (0, 0, 1))
        axis_vector = np.asarray(axis_vector, dtype=float)
        if np.linalg.norm(axis_vector) == 0:
            axis_vector = np.array([0.0, 0.0, 1.0])

        def _bottom_face_xy_anchor(mesh: Trimesh) -> np.ndarray:
            bounds = mesh.bounds
            bottom_z = float(bounds[0, 2])
            vertices = np.asarray(mesh.vertices, dtype=float)
            if len(vertices) == 0:
                return np.array([0.0, 0.0], dtype=float)
            tolerance = max(0.1, float(np.max(mesh.extents)) * 0.005)
            bottom_vertices = vertices[np.isclose(vertices[:, 2], bottom_z, atol=tolerance)]
            if len(bottom_vertices) == 0:
                bottom_vertices = vertices[vertices[:, 2] <= bottom_z + tolerance]
            if len(bottom_vertices) == 0:
                return np.asarray(mesh.centroid[:2], dtype=float)
            return np.mean(bottom_vertices[:, :2], axis=0)

        def _bottom_face_z(mesh: Trimesh) -> float:
            bounds = mesh.bounds
            bottom_z = float(bounds[0, 2])
            vertices = np.asarray(mesh.vertices, dtype=float)
            if len(vertices) == 0:
                return bottom_z
            tolerance = max(0.1, float(np.max(mesh.extents)) * 0.005)
            bottom_vertices = vertices[np.isclose(vertices[:, 2], bottom_z, atol=tolerance)]
            if len(bottom_vertices) == 0:
                bottom_vertices = vertices[vertices[:, 2] <= bottom_z + tolerance]
            if len(bottom_vertices) == 0:
                return bottom_z
            return float(np.mean(bottom_vertices[:, 2]))

        if abs(float(orientation_yaw_deg)) > 1e-6:
            solid_bounds = solid_mesh.bounds
            solid_center = (solid_bounds[0] + solid_bounds[1]) / 2.0
            rotation_matrix = trimesh.transformations.rotation_matrix(
                np.deg2rad(float(orientation_yaw_deg)),
                axis_vector,
                point=solid_center,
            )
            solid_mesh.apply_transform(rotation_matrix)

        # === 벌떡 세우기: translation 전에 항상 모델을 지정 축으로 회전 ===
        try:
            bounds = solid_mesh.bounds
            sizes = {
                "X": bounds[1, 0] - bounds[0, 0],
                "Y": bounds[1, 1] - bounds[0, 1],
                "Z": bounds[1, 2] - bounds[0, 2],
            }
            largest_axis = max(sizes.items(), key=lambda x: x[1])[0]
            target_axis = {
                "Z축(기본)": "Z",
                "Y축": "Y",
                "X축": "X",
            }.get(upright_target_axis, "Z")
            if largest_axis != target_axis:
                center = (bounds[0] + bounds[1]) / 2.0
                if largest_axis == "X" and target_axis == "Z":
                    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0], point=center)
                elif largest_axis == "Y" and target_axis == "Z":
                    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0], point=center)
                elif largest_axis == "Z" and target_axis == "X":
                    rot = trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0], point=center)
                elif largest_axis == "Z" and target_axis == "Y":
                    rot = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0], point=center)
                elif largest_axis == "X" and target_axis == "Y":
                    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1], point=center)
                elif largest_axis == "Y" and target_axis == "X":
                    rot = trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 0, 1], point=center)
                else:
                    rot = None
                if rot is not None:
                    logger.info(f"Upright rotation: largest axis {largest_axis} -> rotate to {target_axis}")
                    solid_mesh.apply_transform(rot)
        except Exception:
            logger.warning("Upright rotation failed, continuing without it")

        # Align the character mesh to sit on top of the base cap.
        base_bounds = base_mesh.bounds
        solid_bounds = solid_mesh.bounds
        if xy_alignment_mode == "centroid":
            base_xy_anchor = np.asarray(base_mesh.centroid[:2], dtype=float)
            solid_xy_anchor = np.asarray(solid_mesh.centroid[:2], dtype=float)
        elif xy_alignment_mode == "bottom_face":
            base_xy_anchor = _bottom_face_xy_anchor(base_mesh)
            solid_xy_anchor = _bottom_face_xy_anchor(solid_mesh)
        else:
            base_xy_anchor = (base_bounds[0, :2] + base_bounds[1, :2]) / 2.0
            solid_xy_anchor = (solid_bounds[0, :2] + solid_bounds[1, :2]) / 2.0

        base_xy = base_bounds[1, :2] - base_bounds[0, :2]
        solid_xy = solid_bounds[1, :2] - solid_bounds[0, :2]
        scale_candidates = []
        for axis in range(2):
            if solid_xy[axis] > 0:
                scale_candidates.append((base_xy[axis] * fit_ratio) / solid_xy[axis])
        if scale_candidates:
            scale_factor = min(min(scale_candidates), 1.0)
            if scale_factor < 1.0:
                solid_mesh.apply_scale(scale_factor)
                solid_bounds = solid_mesh.bounds
                if xy_alignment_mode == "centroid":
                    solid_xy_anchor = np.asarray(solid_mesh.centroid[:2], dtype=float)
                elif xy_alignment_mode == "bottom_face":
                    solid_xy_anchor = _bottom_face_xy_anchor(solid_mesh)
                else:
                    solid_xy_anchor = (solid_bounds[0, :2] + solid_bounds[1, :2]) / 2.0

        target_bottom_z = base_bounds[1, 2] - overlap_mm
        bottom_z = _bottom_face_z(solid_mesh)
        translation = np.array([
            base_xy_anchor[0] - solid_xy_anchor[0],
            base_xy_anchor[1] - solid_xy_anchor[1],
            target_bottom_z - bottom_z,
        ], dtype=float)
        solid_mesh.apply_translation(translation)


        # 🌟 Voxel Assembly (안정적인 출력용 병합)
        assembly_mesh = trimesh.util.concatenate([base_mesh, solid_mesh])
        
        # 3. 변경: 사용하지 않는 preview_glb_path 항목 제거
        debug_info = {
            "success": False,
            "alignment_translation": translation.tolist(),
        }

        try:
            fallback_processor = MeshProcessor.__new__(MeshProcessor)
            fallback_processor.raw_data = None
            fallback_processor.format = "glb"
            fallback_processor.mesh = assembly_mesh
            fallback_processor.top_mesh = None
            fallback_processor.bottom_mesh = None

            fallback_pitch = pitch_mm if pitch_mm is not None else max(float(np.max(assembly_mesh.extents)) / 240.0, 0.25)
            merged_mesh, merged_info = fallback_processor.solidify_with_voxels(pitch_mm=fallback_pitch, fill_holes=True)
            
            # 3. 변경: 여기서도 preview_glb_path 지우고 성공 로그만 업데이트
            merged_info.update({
                "success": True,
                "method": "voxel_assembly",
                "alignment_translation": translation.tolist(),
            })
            return merged_mesh, merged_info

        except Exception as e:
            debug_info["error"] = str(e)
            logger.error(f"Voxel assembly failed: {e}")
            return assembly_mesh, debug_info

    def validate_mesh(self, mesh: Trimesh) -> dict:
        """
        Validate mesh for 3D printing viability.
        
        Args:
            mesh: Mesh to validate
            
        Returns:
            Dictionary with validation results
        """
        is_valid = getattr(mesh, 'is_valid', True)
        is_watertight = getattr(mesh, 'is_watertight', False)
        
        results = {
            "is_valid": is_valid,
            "is_watertight": is_watertight,
            "faces_count": len(mesh.faces),
            "vertices_count": len(mesh.vertices),
            "volume": mesh.volume,
            "surface_area": mesh.area,
        }
        
        if not is_watertight:
            logger.warning("Mesh is not watertight - may have issues in 3D printing")
            results["warnings"] = ["Non-watertight mesh"]
        
        return results

    def export_stl(self, mesh: Trimesh, filepath: str) -> bool:
        """
        Export mesh to STL format for 3D printing.
        
        Args:
            mesh: Trimesh object to export
            filepath: Output file path
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            # Export as binary STL (smaller file size)
            mesh.export(filepath, file_type="stl_ascii")
            logger.info(f"Mesh exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting STL: {e}")
            return False

    def export_obj(self, mesh: Trimesh, filepath: str) -> bool:
        """
        Export mesh to OBJ format (for viewing/editing).
        
        Args:
            mesh: Trimesh object to export
            filepath: Output file path
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            mesh.export(filepath, file_type="obj")
            logger.info(f"Mesh exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting OBJ: {e}")
            return False

    def get_mesh_info(self, mesh: Trimesh, before_vertices: Optional[int] = None, before_faces: Optional[int] = None) -> dict:
        """Get detailed mesh information for reporting.
        
        Args:
            mesh: Mesh to analyze
            before_vertices: Vertex count before cavity operation (for comparison)
            before_faces: Face count before cavity operation (for comparison)
        """
        is_valid = getattr(mesh, 'is_valid', True)
        is_watertight = getattr(mesh, 'is_watertight', False)
        
        info = {
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "volume_mm3": float(mesh.volume),
            "surface_area_mm2": float(mesh.area),
            "is_valid": bool(is_valid),
            "is_watertight": bool(is_watertight),
            "bounds": {
                "min": mesh.bounds[0].tolist(),
                "max": mesh.bounds[1].tolist()
            }
        }
        
        # Add cavity operation impact info
        if before_vertices is not None and before_faces is not None:
            info["vertex_change"] = len(mesh.vertices) - before_vertices
            info["face_change"] = len(mesh.faces) - before_faces
            info["cavity_applied"] = len(mesh.faces) < before_faces
        
        return info

