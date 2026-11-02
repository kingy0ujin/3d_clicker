
# Image-to-keycap: AI Custom Clicker Keyring Generator

이미지 한 장(또는 텍스트 설명)을 입력하면 로우폴리 3D 메시를 만들고 키캡 하부와 결합해, 3D 프린팅용 커스텀 클리커 키링 파일을 만들어주는 Gradio 기반 웹 서비스입니다.

## What it does

* 텍스트 설명으로 OpenAI `gpt-image-2` 참조 이미지를 생성하거나, 이미지를 직접 업로드/샘플에서 선택합니다.
* 이미지의 실루엣을 추출해 로컬에서 로우폴리 3D 메시(GLB)를 생성합니다. (GPU, 외부 서버 불필요)
* 생성한 메시를 MX 규격 키캡 하부(STL) 위에 정렬해 결합합니다.
* 결합 시 원본 형상과 텍스처를 유지하고, 닫힌 입체가 아니면 복셀 일체화로 대체합니다.
* 최종 GLB/OBJ와 키링용 하부(STL)를 내려받아 3D 프린팅에 사용합니다.

## Tech Stack

* UI: Gradio
* Image Generation: OpenAI `gpt-image-2`
* 3D Processing: NumPy, SciPy, scikit-image, Trimesh
* Optional Backend: TripoSR (Hugging Face Space)
* Deployment: Docker (Hugging Face Spaces), GitHub Actions
* Environment: Python 3.11+, Windows / macOS / Linux, Python venv

## Project Structure

```
3d_clicker/
├─ app/
│  ├─ main_gradio.py
│  ├─ ui.py
│  ├─ api/
│  │  ├─ __init__.py
│  │  ├─ openai_api.py
│  │  ├─ lowpoly_api.py
│  │  └─ huggingface_api.py
│  ├─ utils/
│  │  ├─ config.py
│  │  ├─ lowpoly_prep.py
│  │  └─ trimesh_utils.py
│  └─ assets/
│     ├─ base_keycap.stl
│     ├─ base_keycap2.stl
│     ├─ examples/
│     └─ samples/
├─ .github/workflows/
├─ ARCHITECTURE.md
├─ QUICKSTART.md
├─ Dockerfile
├─ requirements.txt
└─ run.bat
```

## Screenshots

### [Page 1 - Image Preparation]
<img width="388" height="376" alt="20261101_234225" src="https://github.com/user-attachments/assets/2b598053-08db-4f19-a10c-f19de7638f4a" />

### [Page 2 - 3D Mesh Build]
<img width="340" height="291" alt="20261101_234246" src="https://github.com/user-attachments/assets/a89e0ef7-c107-4f6f-a189-41e1224a4783" />

### [Page 3 - Merge with Base]
<img width="355" height="400" alt="20261101_234426" src="https://github.com/user-attachments/assets/fc1afa23-e5bd-463b-ad2f-1c8af335fccc" />

## Key Files

* `app/main_gradio.py`: 앱 상태 관리와 비즈니스 로직 (`ImageToGoodsApp`)
* `app/ui.py`: Gradio Blocks UI 구성
* `app/api/openai_api.py`: OpenAI 이미지 생성
* `app/api/lowpoly_api.py`: 로컬 로우폴리 3D 생성 (기본 백엔드)
* `app/api/huggingface_api.py`: TripoSR Space 호출 (선택 백엔드)
* `app/utils/lowpoly_prep.py`: 실루엣, 외곽선, 디테일 맵 추출
* `app/utils/trimesh_utils.py`: 메시 로드, 정렬, 직접 결합, 복셀 일체화
* `app/utils/config.py`: 환경변수 기반 설정 (`AppConfig`)
* `app/assets/base_keycap.stl`: 결합용 키캡 하부
* `app/assets/base_keycap2.stl`: 키링용 하부 (다운로드 제공)

## Setup

```
git clone <저장소 주소>
cd 3d_clicker

python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

프로젝트 루트에 `.env` 파일을 만들고 OpenAI API 키를 설정합니다.

```
OPENAI_API_KEY=sk-your-openai-key-here
```

## Run

```
python -m app.main_gradio
```

or

```
run.bat
```

브라우저에서 `http://localhost:7860`에 접속합니다.

## Portfolio Highlights

* 이미지 생성 API 연동과 로컬 3D 변환 파이프라인을 하나의 웹 서비스로 통합
* 실루엣 추출, 삼각분할, 가장자리 라운딩, 어두운 부분 음각 처리로 단일 이미지에서 닫힌 입체 생성
* 직접 결합과 복셀 일체화를 `MERGE_MODE`로 선택하는 결합 전략 설계
* 3단계 UI 흐름(이미지 준비 → 메시 빌드 → 하부 결합)으로 CAD 지식 없이 사용 가능
* Docker 및 GitHub Actions 기반 Hugging Face Spaces 배포 경험(현재는 API 키 보호를 위해 비공개)

## Notes

* 뒷면은 앞면의 거울상이며, 정면 외 방향의 실제 깊이는 표현하지 못합니다.
* 결합 단계에는 키캡 하부 STL이 필요하며, 파일이 없으면 결합이 실패합니다.
* 배경이 투명한 PNG를 쓰면 실루엣이 가장 정확하게 잡힙니다.
* `MERGE_MODE`는 `auto`(기본) / `direct` / `voxel` 중에서 고를 수 있습니다.
* `IMAGE_TO_3D_BACKEND=triposr`는 Hugging Face Space 상태에 따라 동작하지 않을 수 있습니다.
* 앱 시작 시 `OPENAI_API_KEY` 설정 여부를 확인합니다.
* 자세한 구조는 `ARCHITECTURE.md`, 빠른 시작은 `QUICKSTART.md`를 참고하세요.

## License

MIT License


