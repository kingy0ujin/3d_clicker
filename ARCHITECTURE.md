# 🏗️ Image-to-keycap 시스템 아키텍처

## 전체 파이프라인

```
사용자 디자인 묘사 텍스트 입력
        ↓
[Step 1] OpenAI gpt-image-2 API
        ↓ (30초)
정측면 2D 캐릭터 이미지 생성 및 로드 (gr.Image)
        ↓
[Step 2] TripoSR 3D (gradio client)
        ↓ (50초)
단일 이미지 → 3D 메시 데이터 생성 (영문 원본 .glb 바이트 데이터 확보)
        ↓
[Step 3] Trimesh & Voxel 엔진 처리 (로컬 서버)
        ↓ (30초)
        ├─ 3D 모델 크기 자동 스케일링 (Target Height) 및 세우기 회전
        ├─ 키링용 기계식 스위치 하단부(base_keycap.stl) 상단에 캐릭터 정렬/배치
        ├─ 두 모델 객체 단순 병합 (trimesh.util.concatenate)
        └─ [핵심] Voxel Solidification (오류 없는 3D 출력을 위한 단색 일체화 작업)
        ↓
[Step 4] 최종 다운로드 및 3D 인쇄
        ↓
최종 결합본(.glb / .obj) 또는 키링용 하단부 단독(.stl) 다운로드
        ↓
3D 프린터 출력 후 체리축 스위치 조립 → 나만의 커스텀 클리커 완성!
```

---

## 시스템 구성도

```
┌─────────────────────────────────────────────────────────┐
│                    Gradio Web UI (blocks)               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Text Input  │  │ Image Viewer │  │  3D Viewer   │    │
│  │   Widget    │  │  (gr.Image)  │  │ (gr.Model3D) │    │
│  └─────────────┘  └──────────────┘  └──────────────┘    │
└──────────────┬──────────────────────────────────────────┘
               │
        ┌──────┴───────┐
        │              │
    ┌───▼────┐    ┌───▼────┐
    │ OpenAI │    │TripoSR │
    │  API   │    │  API   │
    └───┬────┘    └───┬────┘
        │              │
        ▼              ▼
    Generated       3D Mesh
    2D Image       Raw Bytes
        │              │
        └──────┬───────┘
               │
        ┌──────▼────────────┐
        │   Trimesh Engine  │
        │  ┌──────────────┐ │
        │  │ Scale & Align│ │
        │  │ Concatenate  │ │
        │  │Voxel Solidify│ │
        │  └──────────────┘ │
        └──────┬────────────┘
               │
        ┌──────▼──────────────┐
        │    Final Outputs    │
        │ ├─ final_merged.glb │
        │ ├─ final_merged.obj │
        └─────────────────────┘
```

---

## 파일 구조 및 역할

```
aiweb_clicker/
│
├── 🎨 UI Layer (네온 그린 CRT 레트로 테마)
│   └── app/ui.py                  # Gradio 인터페이스 구성 (`create_ui`)
│       - gr.Blocks 기반 3페이지 단계별 레이아웃
│       - gr.Image, gr.Model3D 활용 (에디터/크롭 제거로 단순 뷰어 최적화)
│       - 읽기 전용 상태창(.status-content-only) 글자색 짙은 초록색 제어
│
├── 🔌 API Integration Layer
│   └── app/api.py                 # 인공지능 API 모델 클래스 정의
│       - OpenAIImageGenerator: gpt-image-2 기반 이미지 생성
│       - TripoSRModel: 단일 이미지의 3D 공간 메쉬 복원 추론
│
├── ⚙️ Processing & Core Layer
│   └── app/utils.py               # 유틸리티 및 코어 프로세서 엔진
│       - AppConfig: 환경 변수 관리 및 시스템 로그 세팅
│       - MeshProcessor: 3D 프린팅 viability를 위한 실질적 메시 가공 변환
│           └─ 타겟 높이 자동 스케일링, 복셀 기반 단색화 병합 (`solidify_with_voxels`)
│
├── 🚀 Application Entry
│   └── app/main_gradio.py         # 메인 앱 컨트롤러 (`ImageToGoodsApp`)
│       - 전역 애플리케이션 상태 관리 및 백엔드 연동 비즈니스 로직
│       - UI 이벤트와 가공 엔진 간 데이터 브릿지 역할 및 파일 다운로드 라우팅
│
├── 🐳 Deployment
│   ├── Dockerfile                 # Hugging Face Spaces 전용 Docker 빌드 설정
│   └── .dockerignore
│
└── 📦 Dependencies
    └── requirements.txt          # 프로젝트 의존성 패키지 (trimesh, gradio, scipy 등)
```

