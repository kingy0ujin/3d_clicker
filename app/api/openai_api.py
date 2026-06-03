"""
OpenAI Image Generation API Integration
Generates optimal side-profile images for 3D reconstruction using gpt-image-2
"""

import base64
import logging
from io import BytesIO
from typing import Optional

from PIL import Image
from openai import OpenAI, RateLimitError, APIError

logger = logging.getLogger(__name__)


class OpenAIImageGenerator:
    """
    Generates isometric/side-profile images optimized for 3D reconstruction
    by directly calling OpenAI's flagship image engine (gpt-image-2).
    """

    # Default prompt template changed to a front-facing, face-centric square crop template
    # Optimized for keycap-top-friendly imagery (face/head centered, square, minimal background)
    SIDE_PROFILE_PROMPT_TEMPLATE = """
    정면 클로즈업 - 키캡 상부용 참조 이미지

    객체(OBJECT CONCEPT): {concept}

    필수 요구사항 (3D 생성/복원을 위해):
    1) 구도: 정면(Frontal) 클로즈업, 얼굴 또는 머리 중심으로 이미지 중앙에 정확히 배치. (Head/face centered)
    2) 종횡비: 정사각형 1:1 (square, 1:1 aspect ratio)
    3) 보이는 범위: 얼굴만(목/어깨/상반신 제외). 얼굴과 귀만 포함하고 목은 보이지 않도록 합니다.
    4) 배경: 단색 또는 투명(transparent) 배경만 사용. 그림자, 그라데이션, 반사 불허.
    5) 스타일: 매트한 표면, 하이라이트나 반사 없는 조명, 고해상도 디테일 강조
    6) 시선: 눈은 정면을 응시하도록 (eyes looking forward)
    7) 불필요 요소 금지: full body, busy background, text, watermark, side/three-quarter profile 등 제외

    위의 조건을 엄격히 지켜서, 키캡 상부(톱 캡)에 잘 맞는 중앙 집중형 이미지를 생성하십시오.
    """

    def __init__(self, api_key: str):
        """
        Initialize OpenAI client with API key.
        """
        self.client = OpenAI(api_key=api_key)
        # 비용과 일관성 통제를 위해 gpt-5.5 래핑 대신 이미지 엔진 다이렉트 지정
        self.model = "gpt-image-2"
        
    def generate_side_profile_image(
        self,
        concept: str,
        size: str = "1024x1024"
    ) -> Optional[Image.Image]:
        """
        Generate a 3D modeling reference image (side profile) optimized for TripoSR reconstruction.
        Returns a PIL Image object decoded from native b64_json response.
        """
        try:
            # 베이스 프롬프트 조립 (gpt-image-2 엔진에 직접 주입됨)
            prompt = self.SIDE_PROFILE_PROMPT_TEMPLATE.format(concept=concept)
            
            logger.info(f"Directly requesting gpt-image-2 for concept: {concept}")
            
            # gpt-image-2 전용 고성능 직공 파이프라인
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                n=1,
                size=size,
                #response_format="b64_json"  # gpt-image-2의 네이티브 규격 명시
            )
            
            # 응답 객체에서 직접 base64 데이터 추출 (gpt-image-2 표준 파싱)
            image_b64 = response.data[0].b64_json
            
            if not image_b64:
                logger.error("API response succeeded but b64_json data field is empty.")
                return None
                
            # Base64 스트링 디코딩 후 PIL Image 객체 생성
            image_bytes = base64.b64decode(image_b64)
            image = Image.open(BytesIO(image_bytes))
            
            logger.info(f"✓ Image successfully generated and decoded: {image.size}")
            return image
            
        except RateLimitError as e:
            logger.error(f"OpenAI API rate limit hit: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during gpt-image-2 generation: {e}")
            raise

    def generate_custom_image(
        self,
        prompt: str,
        size: str = "1024x1024"
    ) -> Optional[Image.Image]:
        """
        Generate 3D modeling reference image with a completely custom prompt layout.
        """
        try:
            logger.info("Generating custom 3D reference image via gpt-image-2 direct call")
            
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                n=1,
                size=size,
                #response_format="b64_json"
            )
            
            image_b64 = response.data[0].b64_json
            if not image_b64:
                return None
                
            return Image.open(BytesIO(base64.b64decode(image_b64)))
            
        except Exception as e:
            logger.error(f"Error generating custom image: {e}")
            raise

    @staticmethod
    def save_image(image: Image.Image, filepath: str) -> None:
        """
        Save PIL Image to local file system for subsequent TripoSR API pipeline transmission.
        """
        image.save(filepath, format="PNG")
        logger.info(f"Image successfully saved to local storage: {filepath}")
