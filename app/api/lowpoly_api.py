"""
Local Low-Poly Generator (AI / GPU / 외부 서버 불필요)

이미지 한 장의 실루엣을 뽑아, 뒤쪽 형상을 추정하는 대신 "부풀린 입체(pillow extrusion)"로
만든 로우폴리 메시(.glb)를 생성한다.

  1. 실루엣 마스크 추출 (알파 채널 또는 테두리 배경색 기준)
  2. 외곽선 + 내부 격자 점 + 이미지의 색 경계선/어두운 부분 점으로 삼각분할 (Delaunay)
  3. 가장자리는 둥글게 깎고(bevel) 가운데는 평평하게 두께를 주어 앞/뒤 면을 만들고,
     옆면으로 연결 -> 닫힌(watertight) 입체
  4. 어두운 부분(눈, 입, 선)은 앞면을 안쪽으로 새겨서(음각) 단색으로 출력해도 보이게 함
  5. 색은 원본 이미지를 텍스처로 입혀서 미리보기와 GLB 에 사용

좌표계: TripoSR GLB 와 동일하게 Y축이 높이, 앞면이 +Z 를 향한다. 단위는 mm 이고 가장 긴 변이 100mm.
"""

import logging
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage
from scipy.spatial import Delaunay, cKDTree

from ..utils.lowpoly_prep import (
    WORK_PAD,
    detail_maps,
    feature_points,
    outline_points,
    prepare_inputs,
)

logger = logging.getLogger(__name__)


class LowPolyModel:
    """이미지 -> 로우폴리 3D 메시. 다른 백엔드와 같은 generate_3d_mesh 인터페이스를 가진다."""

    TARGET_SIZE_MM = 100.0  # 가장 긴 변의 길이
    MAX_HALF_THICK_RATIO = 0.14  # 앞/뒤 한쪽 최대 두께 / 가장 긴 변 (전체 두께는 약 28%)
    MIN_HALF_THICK_RATIO = 0.02  # 가장자리의 최소 한쪽 두께 / 가장 긴 변
    BEVEL_RATIO = 0.07  # 가장자리를 둥글게 깎는 폭 / 가장 긴 변
    ENGRAVE_RATIO = 0.03  # 어두운 부분을 새기는 최대 깊이 / 가장 긴 변
    ENGRAVE_MAX_FRACTION = 0.6  # 새김 깊이는 그 지점 두께의 이 비율을 넘지 않는다 (뚫림 방지)

    def __init__(self):
        logger.info("Initializing local Low-Poly generator (no network required)")

    @staticmethod
    def _fail(message: str) -> Dict[str, Any]:
        return {"success": False, "error": message}

    @staticmethod
    def _spacing_from_resolution(resolution: int, mask_shape: Tuple[int, int]) -> float:
        """UI 해상도(32~320)를 내부 점 간격(px)으로 바꾼다. 클수록 삼각형이 많아진다."""
        cells_across = float(np.clip(resolution / 10.0, 6.0, 40.0))
        return max(2.0, max(mask_shape) / cells_across)

    @staticmethod
    def _interior_points(mask: np.ndarray, dist: np.ndarray, spacing: float) -> np.ndarray:
        """마스크 안쪽에 육각 격자 모양으로 점을 흩뿌린다 (경계에서 너무 가까운 점은 제외)."""
        row_step = spacing * np.sqrt(3.0) / 2.0
        points = []
        for i, row in enumerate(np.arange(0.0, mask.shape[0], row_step)):
            offset = 0.5 * spacing if i % 2 else 0.0
            for col in np.arange(offset, mask.shape[1], spacing):
                r, c = int(round(row)), int(round(col))
                if r < mask.shape[0] and c < mask.shape[1] and dist[r, c] >= 0.6 * spacing:
                    points.append((row, col))
        return np.asarray(points, dtype=np.float64).reshape(-1, 2)

    @staticmethod
    def _inside(mask_lenient: np.ndarray, pts_rc: np.ndarray) -> np.ndarray:
        rows = np.clip(np.rint(pts_rc[:, 0]).astype(int), 0, mask_lenient.shape[0] - 1)
        cols = np.clip(np.rint(pts_rc[:, 1]).astype(int), 0, mask_lenient.shape[1] - 1)
        return mask_lenient[rows, cols]

    @staticmethod
    def _remove_pinch_triangles(simplices: np.ndarray, vertex_count: int) -> np.ndarray:
        """
        바깥 경계의 한 점에 경계 변이 3개 이상 모이는 "꼬집힌(pinch)" 정점을 없앤다.
        이런 정점이 있으면 앞/뒤를 이은 옆면이 닫히지 않아 watertight 가 깨진다.
        꼬집힌 정점에 붙은 경계 삼각형을 하나씩 제거하며 더 이상 없을 때까지 반복한다.
        """
        for _ in range(50):
            edges = np.sort(
                np.vstack([simplices[:, [0, 1]], simplices[:, [1, 2]], simplices[:, [2, 0]]]), axis=1
            )
            unique_edges, inverse, counts = np.unique(
                edges, axis=0, return_inverse=True, return_counts=True
            )
            rim_mask = counts == 1
            degree = np.bincount(unique_edges[rim_mask].ravel(), minlength=vertex_count)
            pinch = np.where(degree > 2)[0]
            if len(pinch) == 0:
                break

            tri_edge_ids = np.asarray(inverse).ravel().reshape(3, -1).T  # 삼각형별 세 변의 id
            on_rim = rim_mask[tri_edge_ids].any(axis=1)
            touches_pinch = np.isin(simplices, pinch).any(axis=1)
            candidates = np.where(on_rim & touches_pinch)[0]
            if len(candidates) == 0:
                break
            # 한 번에 하나씩만 제거한다 (한꺼번에 지우면 모양이 크게 깎인다)
            simplices = np.delete(simplices, candidates[0], axis=0)
        return simplices

    def _triangulate(
        self,
        mask: np.ndarray,
        spacing: float,
        extra_points: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        (points_rc, triangles, dist) 를 돌려준다. 삼각형은 마스크 안쪽에 있는 것만 남긴다.
        extra_points: 이미지의 색 경계선/눈 같은 특징점. 격자 점과 너무 가까우면 격자 점을 뺀다.
        """
        dist = ndimage.distance_transform_edt(mask)
        boundary = outline_points(mask, spacing)
        interior = self._interior_points(mask, dist, spacing)
        if extra_points is not None and len(extra_points) and len(interior):
            near = cKDTree(extra_points).query(interior, k=1)[0] < 0.7 * spacing
            interior = interior[~near]
        parts = [boundary]
        if len(interior):
            parts.append(interior)
        if extra_points is not None and len(extra_points):
            parts.append(extra_points)
        points = np.unique(np.round(np.vstack(parts), 3), axis=0)

        tri = Delaunay(points[:, ::-1])  # (x=col, y=row)
        simplices = tri.simplices

        lenient = ndimage.binary_dilation(mask, iterations=1)
        a, b, c = (points[simplices[:, k]] for k in range(3))
        keep = self._inside(lenient, (a + b + c) / 3.0)
        for p, q in ((a, b), (b, c), (c, a)):
            keep &= self._inside(lenient, (p + q) / 2.0)
        simplices = simplices[keep]
        simplices = self._remove_pinch_triangles(simplices, len(points))
        if len(simplices) < 4:
            raise ValueError("삼각분할 결과가 너무 적습니다 (이미지에서 물체가 너무 작거나 단순합니다)")
        return points, simplices, dist
    def _thickness(
        self, dist: np.ndarray, dark: np.ndarray, points: np.ndarray, size_px: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        점마다 (앞면 z, 뒷면 z) 를 mm 로 계산한다.

        - 가장자리는 1/4 원 모양(bevel)으로 둥글게 깎고, 안쪽은 거의 평평하게 둔다.
          (예전에는 거리^0.6 이라 몸 전체가 달걀처럼 부풀었다)
        - 어두운 부분(눈, 입, 선)은 앞면만 안쪽으로 새겨서 3D 프린트 후에도 보이게 한다.
        """
        # 거리 변환은 픽셀 단위 계단/능선이 있어서 그대로 쓰면 표면이 울퉁불퉁해진다 -> 부드럽게 만든다
        dist = ndimage.gaussian_filter(dist, sigma=max(1.0, size_px / 90.0))
        rows = np.clip(np.rint(points[:, 0]).astype(int), 0, dist.shape[0] - 1)
        cols = np.clip(np.rint(points[:, 1]).astype(int), 0, dist.shape[1] - 1)
        d = dist[rows, cols]

        mm_per_px = self.TARGET_SIZE_MM / size_px
        d_mm = d * mm_per_px
        max_half = self.MAX_HALF_THICK_RATIO * self.TARGET_SIZE_MM
        min_half = self.MIN_HALF_THICK_RATIO * self.TARGET_SIZE_MM
        bevel = max(self.BEVEL_RATIO * self.TARGET_SIZE_MM, 1e-3)
        # 얇은 부위(팔, 다리)는 두께가 폭의 절반을 넘지 않게 해서 납작한 막대처럼 되는 것을 막는다
        local_cap = np.minimum(max_half, np.maximum(min_half, d_mm * 1.1))

        t = np.clip(d_mm / bevel, 0.0, 1.0)
        round_profile = np.sqrt(1.0 - (1.0 - t) ** 2)  # 가장자리에서 가파르게 올라가는 1/4 원
        half = min_half + (local_cap - min_half) * round_profile

        dk = dark[rows, cols]
        engrave = np.clip(dk, 0.0, 1.0) * self.ENGRAVE_RATIO * self.TARGET_SIZE_MM
        engrave = np.minimum(engrave, self.ENGRAVE_MAX_FRACTION * half)
        engrave = np.where(d_mm > 0.9 * bevel, engrave, 0.0)  # 가장자리 근처는 새기지 않는다

        return half - engrave, -half

    def _make_texture(self, texture_rgb: np.ndarray) -> Image.Image:
        return Image.fromarray(np.ascontiguousarray(texture_rgb)).convert("RGB")

    def _uv_for(self, points: np.ndarray, mask_shape: Tuple[int, int], tex_shape: Tuple[int, int]) -> np.ndarray:
        """작업 해상도 점 좌표(row, col)를 텍스처 UV 로 바꾼다 (텍스처는 WORK_PAD 테두리가 없다)."""
        h, w = mask_shape
        inner_h, inner_w = h - 2 * WORK_PAD, w - 2 * WORK_PAD
        u = np.clip((points[:, 1] - WORK_PAD) / max(inner_w, 1), 0.0, 1.0)
        v = np.clip(1.0 - (points[:, 0] - WORK_PAD) / max(inner_h, 1), 0.0, 1.0)
        return np.column_stack([u, v])

    def _build_mesh(
        self,
        rgb: np.ndarray,
        mask: np.ndarray,
        texture_rgb: np.ndarray,
        resolution: int,
    ) -> trimesh.Trimesh:
        """실루엣을 가장자리가 둥글고 디테일이 새겨진 닫힌 로우폴리 메시로 만든다."""
        spacing = self._spacing_from_resolution(resolution, mask.shape)
        dist_full = ndimage.distance_transform_edt(mask)
        dark, grad = detail_maps(rgb, mask)
        extra = feature_points(dark, grad, dist_full, spacing)
        points, tris, dist = self._triangulate(mask, spacing, extra_points=extra)
        n = len(points)

        # 픽셀 -> mm. x=열, y=높이(위쪽이 +), 가장 긴 변이 TARGET_SIZE_MM
        size_px = float(max(mask.shape))
        scale = self.TARGET_SIZE_MM / size_px
        x = (points[:, 1] - mask.shape[1] / 2.0) * scale
        y = (mask.shape[0] / 2.0 - points[:, 0]) * scale
        z_front, z_back = self._thickness(dist, dark, points, size_px)

        front = np.column_stack([x, y, z_front])
        back = np.column_stack([x, y, z_back])
        vertices = np.vstack([front, back])

        # 이미지 좌표(y 반전)로 만들었으므로 앞면이 +Z 를 향하도록 삼각형 방향을 맞춘다
        tri_xy = np.column_stack([x, y])
        a, b, c = (tri_xy[tris[:, k]] for k in range(3))
        cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        tris = np.where((cross < 0)[:, None], tris[:, ::-1], tris)

        front_faces = tris
        back_faces = tris[:, ::-1] + n

        # 옆면: 삼각분할 바깥 경계(한 번만 쓰인 변)를 앞/뒤로 이어 붙인다
        edges = np.sort(np.vstack([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
        unique_edges, counts = np.unique(edges, axis=0, return_counts=True)
        rim_edges = unique_edges[counts == 1]
        directed = {}
        for tri in tris:
            for i in range(3):
                directed[(int(tri[i]), int(tri[(i + 1) % 3]))] = True
        side_faces = []
        for u, v in rim_edges:
            u, v = int(u), int(v)
            if (u, v) not in directed:
                u, v = v, u
            side_faces.append((u, v, v + n))
            side_faces.append((u, v + n, u + n))

        faces = np.vstack([front_faces, back_faces, np.asarray(side_faces, dtype=np.int64)])

        # 색: 원본 이미지를 텍스처로 입힌다. 앞/뒷면은 같은 UV(뒷면은 거울상), 옆면은 UV 가 가리키는
        # 가장자리 색이 늘어나 보이도록 같은 점의 UV 를 쓴다.
        uv_pts = self._uv_for(points, mask.shape, texture_rgb.shape[:2])
        uv = np.vstack([uv_pts, uv_pts])
        texture = self._make_texture(texture_rgb)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        mesh.visual = trimesh.visual.texture.TextureVisuals(
            uv=uv,
            material=trimesh.visual.material.SimpleMaterial(image=texture),
        )
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        trimesh.repair.fix_normals(mesh)
        return mesh

    def generate_3d_mesh(
        self,
        image: Image.Image,
        remove_background: bool = True,
        foreground_ratio: float = 0.85,
        marching_cubes_resolution: int = 256,
    ) -> Optional[Dict[str, Any]]:
        """
        이미지에서 로우폴리 메시를 만든다.

        Args:
            image: 입력 이미지 (알파 채널이 있으면 그것을 실루엣으로 사용)
            remove_background: 알파 채널이 없을 때 테두리 색을 배경으로 보고 제거할지 여부
            foreground_ratio: 호환용 인자 (사용하지 않음)
            marching_cubes_resolution: UI 의 해상도 슬라이더 값. 클수록 삼각형이 많아진다.

        Returns:
            {"success": True, "mesh_data": glb_path, ...} 또는 {"success": False, "error": str}
        """
        try:
            logger.info("Generating low-poly mesh locally...")
            rgb, mask, texture_rgb = prepare_inputs(image, remove_background)
            logger.info(
                f"Work size: {mask.shape[1]}x{mask.shape[0]}px, silhouette px={int(mask.sum())}, "
                f"texture={texture_rgb.shape[1]}x{texture_rgb.shape[0]}px"
            )

            mesh = self._build_mesh(rgb, mask, texture_rgb, int(marching_cubes_resolution))
            logger.info(
                f"Low-poly mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces, "
                f"watertight={mesh.is_watertight}"
            )

            out_dir = Path(tempfile.gettempdir()) / "lowpoly_output"
            out_dir.mkdir(parents=True, exist_ok=True)
            glb_path = out_dir / f"lowpoly_{uuid.uuid4().hex}.glb"
            mesh.export(str(glb_path), file_type="glb")

            return {
                "mesh_data": str(glb_path),
                "mesh_data_obj": None,
                "format": "glb",
                "success": True,
            }
        except Exception as e:
            logger.error(f"Low-poly generation failed: {e}")
            traceback.print_exc()
            return self._fail(f"로우폴리 생성 실패: {type(e).__name__}: {e}")

