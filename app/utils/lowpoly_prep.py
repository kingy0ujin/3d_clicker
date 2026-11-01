"""
Low-poly 변환용 이미지 전처리 (AI/GPU/네트워크 불필요)

- 알파 채널 또는 테두리 배경색 추정으로 실루엣 마스크를 만든다.
- 마스크를 정리(노이즈 제거, 가장 큰 덩어리만 유지, 구멍 메우기)하고 작업 해상도로 줄인다.
- 마스크 외곽선을 단순화해서 로우폴리용 경계 점을 만든다.
"""

import logging
from typing import Tuple

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

logger = logging.getLogger(__name__)

MAX_WORK_SIDE = 256  # 작업용 최대 변 길이(px)
_PAD = 6


def _extract_mask(image: Image.Image, remove_background: bool) -> Tuple[np.ndarray, np.ndarray]:
    """RGB 배열과 실루엣 마스크(bool)를 반환한다."""
    rgba = np.asarray(image.convert("RGBA"))
    rgb = rgba[..., :3]
    alpha = rgba[..., 3]

    if (alpha < 250).mean() > 0.005:
        logger.info("Using alpha channel as silhouette")
        return rgb, alpha > 127

    if not remove_background:
        logger.info("Background removal disabled: using the whole image as silhouette")
        return rgb, np.ones(alpha.shape, dtype=bool)

    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(np.float32)
    bg = np.median(border, axis=0)
    border_noise = float(np.percentile(np.linalg.norm(border - bg, axis=1), 90))
    threshold = max(35.0, 2.5 * border_noise)
    dist = np.linalg.norm(rgb.astype(np.float32) - bg, axis=2)
    logger.info(f"Background color={bg.astype(int).tolist()}, threshold={threshold:.1f}")
    return rgb, dist > threshold


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    """노이즈 제거 후 가장 큰 덩어리만 남기고 내부 구멍을 메운다."""
    mask = ndimage.binary_closing(mask, iterations=2)
    mask = ndimage.binary_opening(mask, iterations=1)
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    sizes = ndimage.sum(mask, labels, index=np.arange(1, count + 1))
    mask = labels == (int(np.argmax(sizes)) + 1)
    return ndimage.binary_fill_holes(mask)


TEXTURE_MAX_SIDE = 1024  # 텍스처 최대 변 길이(px)
WORK_PAD = 2  # 작업 마스크에 둘러준 빈 테두리(px). UV 계산에 사용된다.


def _bleed_colors(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    물체 바깥(과 흰 배경이 섞인 가장자리) 픽셀을 가장 가까운 물체 안쪽 색으로 채운다.
    텍스처를 늘려 샘플링할 때 배경색이 번지거나 흰 테두리가 생기는 것을 막는다.
    """
    iterations = max(2, int(round(max(mask.shape) / 200.0)))
    core = ndimage.binary_erosion(mask, iterations=iterations)
    if int(core.sum()) < 16:
        core = mask
    idx = ndimage.distance_transform_edt(~core, return_distances=False, return_indices=True)
    return rgb[idx[0], idx[1]]


def prepare_inputs(
    image: Image.Image, remove_background: bool
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    실루엣 영역으로 잘라서 다음 세 가지를 반환한다.

    - rgb: 작업 해상도(최대 MAX_WORK_SIDE) 색 이미지 (마스크와 같은 크기, 테두리 WORK_PAD 포함)
    - mask: 작업 해상도 실루엣 마스크 (bool)
    - texture: 텍스처용 고해상도 색 이미지 (테두리 없음, 최대 TEXTURE_MAX_SIDE)
    """
    rgb, mask = _extract_mask(image, remove_background)

    mask = np.pad(mask, _PAD)
    rgb = np.pad(rgb, ((_PAD, _PAD), (_PAD, _PAD), (0, 0)), mode="edge")
    mask = _clean_mask(mask)
    if not mask.any():
        raise ValueError("이미지에서 물체를 찾지 못했습니다 (배경 제거 결과가 비어 있음)")

    ys, xs = np.where(mask)
    margin = 3
    r0, r1 = max(ys.min() - margin, 0), min(ys.max() + margin + 1, mask.shape[0])
    c0, c1 = max(xs.min() - margin, 0), min(xs.max() + margin + 1, mask.shape[1])
    mask, rgb = mask[r0:r1, c0:c1], rgb[r0:r1, c0:c1]

    rgb = _bleed_colors(rgb, mask)
    height, width = mask.shape

    def _resize_rgb(arr: np.ndarray, new_w: int, new_h: int) -> np.ndarray:
        return np.asarray(Image.fromarray(np.ascontiguousarray(arr)).resize((new_w, new_h), Image.LANCZOS))

    tex_scale = min(1.0, TEXTURE_MAX_SIDE / max(height, width))
    if tex_scale < 1.0:
        texture = _resize_rgb(rgb, max(8, int(round(width * tex_scale))), max(8, int(round(height * tex_scale))))
    else:
        texture = rgb.copy()

    work_scale = min(1.0, MAX_WORK_SIDE / max(height, width))
    if work_scale < 1.0:
        new_w, new_h = max(8, int(round(width * work_scale))), max(8, int(round(height * work_scale)))
        rgb = _resize_rgb(rgb, new_w, new_h)
        mask_img = Image.fromarray(mask.astype(np.uint8) * 255).resize((new_w, new_h), Image.BILINEAR)
        mask = np.asarray(mask_img) > 127

    # 외곽선이 항상 닫히도록 빈 테두리를 한 번 더 둔다
    mask = ndimage.binary_fill_holes(np.pad(mask, WORK_PAD))
    rgb = np.pad(rgb, ((WORK_PAD, WORK_PAD), (WORK_PAD, WORK_PAD), (0, 0)), mode="edge")
    return rgb, mask, texture


def outline_points(mask: np.ndarray, spacing: float) -> np.ndarray:
    """마스크의 가장 긴 외곽선을 단순화하고 간격 spacing 이하로 쪼갠 (row, col) 점 배열."""
    contours = measure.find_contours(mask.astype(np.float32), 0.5)
    if not contours:
        raise ValueError("외곽선을 찾지 못했습니다")
    contour = max(contours, key=len)

    polygon = measure.approximate_polygon(contour, tolerance=max(0.8, 0.35 * spacing))
    if len(polygon) > 1 and np.allclose(polygon[0], polygon[-1]):
        polygon = polygon[:-1]
    if len(polygon) < 3:
        raise ValueError("외곽선이 너무 단순해서 입체를 만들 수 없습니다")

    points = []
    for i in range(len(polygon)):
        p0, p1 = polygon[i], polygon[(i + 1) % len(polygon)]
        segments = max(1, int(np.ceil(np.linalg.norm(p1 - p0) / (1.3 * spacing))))
        for k in range(segments):
            points.append(p0 + (p1 - p0) * (k / segments))
    return np.asarray(points, dtype=np.float64)


def detail_maps(rgb: np.ndarray, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    이미지의 디테일 정보를 두 장의 맵으로 만든다 (작업 해상도, mask 와 같은 크기).

    - dark: 0~1. 주변보다 어두운 부분(눈, 입, 선 등). 음각(새김) 깊이에 쓴다.
    - grad: 색이 급격히 바뀌는 곳(경계선)의 세기. 삼각형 꼭짓점을 배치하는 데 쓴다.
    """
    rgbf = rgb.astype(np.float32)
    lum = rgbf @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    lum_s = ndimage.gaussian_filter(lum, 0.8)

    local = ndimage.gaussian_filter(lum, max(3.0, max(mask.shape) / 28.0))
    dark = np.clip((local - lum_s) / 60.0, 0.0, 1.0)
    dark = ndimage.gaussian_filter(dark, 0.7)
    dark = np.where(mask, dark, 0.0)

    smooth = ndimage.gaussian_filter(rgbf, sigma=(0.8, 0.8, 0))
    gx = ndimage.sobel(smooth, axis=1)
    gy = ndimage.sobel(smooth, axis=0)
    grad = np.sqrt((gx ** 2 + gy ** 2).sum(axis=2))
    grad = np.where(mask, grad, 0.0)
    return dark.astype(np.float32), grad.astype(np.float32)


def feature_points(
    dark: np.ndarray, grad: np.ndarray, dist: np.ndarray, spacing: float, max_points: int = 700
) -> np.ndarray:
    """
    색 경계선 위의 점과 어두운 덩어리(눈 등)의 중심점을 (row, col) 로 돌려준다.
    실루엣 경계에 너무 가까운 점은 얇은 삼각형을 만들기 때문에 제외한다.
    """
    from skimage.feature import peak_local_max

    inner = dist >= 0.5 * spacing
    found = []

    g = np.where(inner, grad, 0.0)
    if float(g.max()) > 0:
        edge_pts = peak_local_max(
            g,
            min_distance=max(2, int(round(spacing * 0.3))),
            threshold_abs=0.2 * float(g.max()),
            exclude_border=False,
        )
        if len(edge_pts) > max_points:
            order = np.argsort(-g[edge_pts[:, 0], edge_pts[:, 1]])[:max_points]
            edge_pts = edge_pts[order]
        found.append(edge_pts)

    dk = np.where(inner, dark, 0.0)
    if float(dk.max()) > 0.25:
        blob_pts = peak_local_max(
            dk,
            min_distance=max(2, int(round(spacing * 0.5))),
            threshold_abs=0.3,
            exclude_border=False,
        )
        found.append(blob_pts)

    if not found:
        return np.zeros((0, 2), dtype=np.float64)
    return np.vstack(found).astype(np.float64)
