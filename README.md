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

**단 한 장의 이미지로 조립 가능한 커스텀 클리커 키링을 만드는 웹 서비스**

## 🎯 소개

OpenAI 이미지 생성과 로컬 로우폴리 변환을 결합합니다.
- 텍스트 설명 → OpenAI `gpt-image-2`로 참조 이미지 생성 (또는 직접 업로드 / 샘플 선택)
- 이미지 → **내 PC에서** 로우폴리 3D 메시(GLB) 생성 (GPU, 외부 서버 불필요)
- 3D 메시 → 키캡 하부(STL) 위에 정렬해서 결합
- 최종 GLB/OBJ 다운로드 → 3D 프린팅으로 키캡/키캡 키링 제작

**핵심 특징**
- ✅ CAD 지식 불필요
- ✅ 3D 변환은 로컬 실행 (GPU/외부 서버 불필요)
- ✅ 결합 시 복셀화하지 않고 원본 형상과 텍스처를 유지 (닫힌 입체일 때)
- ✅ 기계식 스위치(MX 규격) 호환 하부 도면 제공

---

## 📋 필수 요구사항

- **Python 3.11+**
- **OpenAI API Key** ([발급](https://platform.openai.com/api-keys))
  - 이미지 생성에만 쓰이지만, 앱 시작 시 키가 설정돼 있는지 확인합니다.

---

## 🚀 로컬 실행

### 1. 환경 설정

```bash
git clone <저장소 주소>
cd 3d_clicker

python -m venv venv
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

프로젝트 루트에 `.env` 파일을 만들고 키를 넣습니다.

```
OPENAI_API_KEY=sk-your-openai-key-here
```

선택 설정 (기본값이 있어서 보통은 필요 없습니다):

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `IMAGE_TO_3D_BACKEND` | `lowpoly` | `lowpoly`(로컬) 또는 `triposr`(HF Space 호출) |
| `MERGE_MODE` | `auto` | `auto` / `direct` / `voxel` (아래 "결합 방식" 참고) |
| `BASE_KEYCAP_MODEL_SOURCE` | `app/assets/base_keycap.stl` | 결합에 쓸 키캡 하부 파일 경로 또는 URL |
| `LOG_LEVEL` | `INFO` | 로그 수준 |
| `TRIPOSR_SPACE_URL` | `stabilityai/TripoSR` | `triposr` 백엔드가 호출할 Gradio Space |
| `HF_API_TOKEN` | (없음) | `triposr` 백엔드의 GPU 쿼터를 늘릴 때만 사용 |

### 4. 실행

```bash
python -m app.main_gradio
```

브라우저에서 `http://localhost:7860`에 접속합니다. (Windows는 `run.bat`으로도 실행할 수 있습니다.)

---

## 📖 사용 방법

### Page 1 — 이미지 준비
- 디자인 설명을 입력하고 **[이미지 생성]** 을 누르거나, 이미지를 업로드하거나, 샘플(`app/assets/samples`)을 불러옵니다.
- 배경이 투명한 PNG를 쓰면 실루엣이 가장 정확하게 잡힙니다.

### Page 2 — 3D 메시 빌드
- **해상도** 슬라이더로 삼각형 수를 조절합니다. 값이 낮을수록 더 로우폴리입니다.
- **배경 투명화**: 알파 채널이 없는 이미지에서 테두리 색을 배경으로 보고 제거합니다.
- **[3D 메시 빌드]** 로 GLB를 만들고, 원본(.glb/.obj)을 내려받을 수 있습니다.

### Page 3 — 하부와 결합
- **축 방향 프리셋**으로 캐릭터가 바라보는 방향을 고른 뒤 **[하부와 결합]** 을 누릅니다.
- 최종 GLB/OBJ와 키링용 하부(`base_keycap2.stl`)를 내려받아 3D 프린터로 출력합니다.
- 출력물에 MX 규격 스위치를 끼워 조립하면 완성입니다.

---

## 🧊 3D 변환 방식 (lowpoly)

한 장의 이미지에서 뒷면을 추정하는 AI 방식이 아니라, **실루엣을 부풀린 입체**를 만듭니다.

1. 알파 채널 또는 테두리 배경색으로 실루엣을 추출합니다.
2. 외곽선, 내부 격자 점, 이미지의 색 경계선/눈 같은 특징점으로 삼각분할합니다.
3. 가장자리는 둥글게 깎고 안쪽은 평평하게 두께를 주어 앞/뒤 면과 옆면을 연결합니다 (닫힌 입체).
4. 어두운 부분(눈, 입, 선)은 앞면을 안쪽으로 새겨서 단색 출력에서도 보이게 합니다.
5. 원본 이미지를 텍스처로 입혀 GLB로 저장합니다.

**한계**: 뒷면은 앞면의 거울상이고, 정면이 아닌 쪽의 형상이나 실제 깊이는 표현하지 못합니다.
`triposr` 백엔드는 HF Space 상태에 따라 동작하지 않을 수 있습니다.

## 🧩 결합 방식 (`MERGE_MODE`)

| 값 | 동작 |
|----|------|
| `auto` (기본) | 캐릭터가 닫힌(watertight) 입체면 **직접 결합**, 아니면 복셀 일체화 |
| `direct` | 직접 결합을 시도하고, 닫힌 입체가 아니면 복셀 일체화 |
| `voxel` | 항상 복셀 일체화 |

- **직접 결합**: 원본 형상과 텍스처가 유지되고 파일이 가볍습니다. 캐릭터와 키캡이 겹친 채로 한 파일에 들어가며, 슬라이서가 겹친 부분을 합쳐서 출력한다고 가정합니다.
- **복셀 일체화**: 격자로 채워 하나의 닫힌 메시로 다시 만들기 때문에 계단 모양이 생기고 색과 세부 디테일이 사라집니다.
- STL로 변환하면 색은 어차피 유지되지 않습니다.

---

## 🔧 기술 스택

| 레이어 | 기술 |
|--------|------|
| UI | Gradio |
| 이미지 생성 | OpenAI `gpt-image-2` |
| 3D 생성 | 로컬 로우폴리 변환 (NumPy, SciPy, scikit-image, Trimesh) |
| 결합 | Trimesh (정렬, 직접 결합, 복셀 일체화) |
| 배포 | Docker (HF Spaces) |

---

## 🛠️ 개발 가이드

### 프로젝트 구조

```
3d_clicker/
├── app/
│   ├── main_gradio.py          # 앱 상태와 비즈니스 로직 (ImageToGoodsApp)
│   ├── ui.py                   # Gradio Blocks UI
│   ├── api/
│   │   ├── __init__.py         # create_mesh_generator(): 백엔드 선택
│   │   ├── openai_api.py       # OpenAI 이미지 생성
│   │   ├── lowpoly_api.py      # 로컬 로우폴리 3D 생성 (기본)
│   │   └── huggingface_api.py  # TripoSR Gradio Space 호출 (선택)
│   ├── utils/
│   │   ├── config.py           # AppConfig (환경변수)
│   │   ├── lowpoly_prep.py     # 실루엣/외곽선/디테일 맵 추출
│   │   └── trimesh_utils.py    # MeshProcessor (로드, 정렬, 결합)
│   └── assets/
│       ├── base_keycap.stl     # 결합용 키캡 하부
│       ├── base_keycap2.stl    # 키링용 하부 (다운로드 제공)
│       ├── examples/           # 매뉴얼 이미지
│       └── samples/            # 샘플 이미지
├── requirements.txt
├── Dockerfile
├── run.bat
└── .github/workflows/sync-to-hf.yml
```

자세한 구조는 [ARCHITECTURE.md](ARCHITECTURE.md), 빠른 시작은 [QUICKSTART.md](QUICKSTART.md)를 참고하세요.

### 주의

- `.gitignore`는 `*.glb`, `*.obj` 같은 생성 파일을 무시하지만 `app/assets/*.stl`은 추적합니다.
- 결합 단계에 쓰는 키캡 하부 파일이 없으면 결합이 실패합니다.

## 📚 참고 자료

- [OpenAI API 문서](https://platform.openai.com/docs/)
- [Trimesh 문서](https://trimesh.org/)
- [Gradio 문서](https://gradio.app/docs/)

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

