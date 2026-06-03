# Image-to-Goods: AI-Driven Custom Clicker Keyring Generator
# Gradio + HuggingFace Spaces 배포용 이미지
#
# 빌드:   docker build -t image-to-goods:latest .
# 실행:   docker run -d -p 7860:7860 --env-file .env image-to-goods:latest
# HF Space에서는 .github/workflows/sync-to-hf.yml이 main push 시 자동 동기화한다.

FROM python:3.11-slim

# 시스템 의존성 (Pillow, trimesh, git 필요)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpng16-16 \
        git \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 설치 (캐시 최적화: requirements.txt만 안 바뀌면 이 레이어 재사용)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 앱 소스 코드 전체 복사
COPY . .

EXPOSE 7860

# 환경변수
# - GRADIO_SERVER_NAME: Gradio 바인딩 (0.0.0.0 = 모든 인터페이스)
# - GRADIO_SERVER_PORT: Gradio 포트
# - PYTHONUNBUFFERED: print/log 즉시 stdout (docker logs로 실시간 확인용)
ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    PYTHONUNBUFFERED=1

# 헬스체크 (메모리 부족으로 죽으면 docker가 자동 재기동)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/').read()" || exit 1

CMD ["python", "-m", "app"]
