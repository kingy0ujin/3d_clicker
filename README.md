---
title: 3d_keycap
emoji: 🍱
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---
# Image-to-keycap: AI Custom Clicker Keyring Generator

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

**단 한 장의 이미지로 조립 가능한 AI 커스텀 클리커 키링을 만드는 웹 서비스**

## 🎯 소개

Image-to-keycap는 OpenAI Image API와 Hugging Face TripoSR API를 결합하여:
- 사용자의 텍스트 설명 → OpenAI gpt-image-2로 정측면 이미지 생성
- 생성된 이미지 → Hugging Face TripoSR로 3D 메시 생성  
- 3D 메시 → Trimesh로 결합 및 단색 일체화 작업
- 최종 obj, glb 도면 다운로드 → 3D 프린팅으로 조립 가능한 실물 키캡/키캡 키링 제작

**핵심 특징:**
- ✅ 누구나 사용 가능 (CAD 지식 불필요)
- ✅ AI 파이프라인 (이미지 생성 → 3D 복원 → 자동 규격 설정)
- ✅ 50초 내 3D 메시 생성 (외부 API 활용)
- ✅ 기계식 스위치 호환성 (MX/클론 표준)

---

## 📋 필수 요구사항

- **Python 3.11+**
- **API Keys:**
  - [OpenAI API Key](https://platform.openai.com/api-keys) - gpt-image-2 사용 
  - [Hugging Face Token](https://huggingface.co/settings/tokens) - 공개 HF Spaces 사용

---

## 🚀 로컬 실행

### 1. 저장소 클론 및 환경 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/aiweb_clicker.git
cd aiweb_clicker

# Python 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일 생성 (`.env.example` 참조):

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키 입력:

```
OPENAI_API_KEY=sk-your-openai-key-here
# HF_API_TOKEN은 선택사항 (공개 HF Spaces 사용)
# HF_API_TOKEN=hf_your_token_here
# BASE_KEYCAP_MODEL_SOURCE=https://your-server/path/to/base_keycap.glb
```

### 4. 애플리케이션 실행

```bash
# Windows (venv 활성화 후)
venv\Scripts\python.exe -m app.main_gradio

# 또는
python -m app.main_gradio
```

브라우저에서 `http://localhost:7860` 접속

---

## 📖 사용 방법

### Step 1️⃣ 아이디어 입력
- 원하는 물건 설명 입력 (예: "귀여운 강아지")
- **[이미지 생성]** 클릭 → 30~40초 대기

### Step 2️⃣ 3D 메시 생성
- **[3D 메시 생성]** 클릭 → 40~50초 대기
- Hugging Face InstantMesh API가 정측면 이미지로부터 다각도 3D 메시 생성

### Step 3️⃣ Trimesh & Voxel 엔진 처리
- 
- **[키캡 하단부와 결합]** 클릭 → 30초 대기
- 두 모델 객체 단순 병합 + 단색 일체화 작업

### Step 4️⃣ 다운로드 및 인쇄

- 3D 프린터로 각각 출력
- 키보드에 결합 -> 키보드 꾸미기
- 기계식 스위치(MX 규격)와 하단부 키캡 모델과 조립 -> 키캡 키링 완성!

---

## 🔧 기술 스택

| 레이어 | 기술 |
|--------|------|
| **UI** | Gradio (웹 프레임워크) |
| **이미지 생성** | OpenAI gpt-image-2 API |
| **3D 생성** | Hugging Face TripoSR API (Gradio Client) |
| **메시 처리** | Trimesh (타겟 높이 자동 스케일링, 축 회전 정렬 및 복셀(Voxel) 병합) |
| **배포** | HF Spaces (Docker), Docker 컨테이너 |

---

## 📊 성능 및 제한사항

| 항목 | 값 |
|------|-----|
| 이미지 생성 시간 | 30초 |
| 3D 메시 생성 시간 | 50초 |
| 메시 처리 | 30초 |
| **총 처리 시간** | **1분 50초 내** |

### API 비용 추정

- OpenAI API: 5$
- Hugging Face: 무료 (Inference API)

---

## 🛠️ 개발 가이드

### 프로젝트 구조

```
aiweb_clicker/
├── app/
│   ├── __init__.py
│   ├── main_gradio.py          # 전역 앱 상태 제어 및 비즈니스 로직 컨트롤러
│   ├── ui.py                   # CRT 복고풍 테마 Gradio Blocks 마크업 구성
│   ├── api.py                  # OpenAI gpt-image-2 및 TripoSR 추론 인터페이스
│   ├── utils.py                # MeshProcessor 가공 엔진 (Voxel Rebuilding 코어)
│   └── assets/
│       ├── base_keycap2.stl    # 기계식 체리축 맞춤형 고정 키링 하단부 도면
│       └── examples/           # 매뉴얼 및 가이드용 프리셋 그래픽 데이터
├── requirements.txt            # 시스템 의존성 라이브러리 목록
├── Dockerfile                  # HF Spaces 컨테이너 패키징 환경 정의서
├── .env.example
└── README.md
```

## 📚 참고 자료

- [OpenAI API 공식 문서](https://platform.openai.com/docs/)
- [Hugging Face Inference API](https://huggingface.co/docs/inference-endpoints/)
- [Trimesh 문서](https://trimesh.org/)
- [Gradio 문서](https://gradio.app/docs/)

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 💬 피드백 및 기여

이슈 보고 및 PR은 언제든지 환영합니다!

---
