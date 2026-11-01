# 🏗️ Image-to-keycap 시스템 아키텍처

## 전체 파이프라인

```
사용자 디자인 묘사 텍스트 입력 (또는 이미지 업로드 / 샘플 선택)
        ↓
[Step 1] OpenAI gpt-image-2 API
        ↓
참조 이미지 생성 및 로드 (gr.Image)
        ↓
[Step 2] 로컬 로우폴리 변환 (LowPolyModel, 외부 서버/GPU 불필요)
        ├─ 실루엣 추출 (알파 채널 또는 테두리 배경색)
        ├─ 외곽선 + 격자 점 + 색 경계선/눈 특징점 → Delaunay 삼각분할
        ├─ 가장자리 둥글게(bevel) + 앞/뒤 면 + 옆면 → 닫힌 입체
        ├─ 어두운 부분(눈, 입, 선) 음각
        └─ 원본 이미지를 텍스처로 입혀 GLB 저장 (가장 긴 변 100mm)
        ↓
[Step 3] Trimesh 결합 (MeshProcessor, 로컬)
        ├─ 크기 보정, 세우기 회전, 축 방향 프리셋 적용
        ├─ 키캡 하부(base_keycap.stl) 위에 정렬/배치
        └─ MERGE_MODE 에 따라 결합
              ├─ direct: 닫힌 입체면 복셀화 없이 그대로 합침 (형상/텍스처 유지)
              └─ voxel : 복셀로 채워 하나의 닫힌 메시로 재구성 (색/디테일 손실)
        ↓
[Step 4] 최종 다운로드 및 3D 인쇄
        ↓
최종 결합본(.glb / .obj) 또는 키링용 하부 단독(.stl) 다운로드
        ↓
3D 프린터 출력 후 스위치 조립 → 나만의 커스텀 클리커 완성
```

---

## 시스템 구성도

```
┌──────────────────────────────────────────────────────────┐
│                   Gradio Web UI (blocks)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Text Input  │  │ Image Viewer │  │  3D Viewer   │     │
│  │   Widget    │  │  (gr.Image)  │  │ (gr.Model3D) │     │
│  └─────────────┘  └──────────────┘  └──────────────┘     │
└───────────────┬──────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
   ┌────▼─────┐    ┌─────▼──────────┐
   │  OpenAI  │    │ create_mesh_   │
   │   API    │    │ generator()    │
   └────┬─────┘    └─────┬──────────┘
        │          ┌─────┴──────────┐
        │     lowpoly (기본)    triposr (선택)
        │     로컬 변환         HF Space 호출
        ▼          └─────┬──────────┘
   Generated             ▼
   2D Image          3D Mesh (.glb)
        │                │
        └───────┬────────┘
                │
        ┌───────▼───────────┐
        │   Trimesh Engine  │
        │  ┌──────────────┐ │
        │  │ Scale & Align│ │
        │  │ Direct Merge │ │
        │  │ (or Voxel)   │ │
        │  └──────────────┘ │
        └───────┬───────────┘
                │
        ┌───────▼─────────────┐
        │    Final Outputs    │
        │ ├─ final_merged.glb │
        │ └─ final_merged.obj │
        └─────────────────────┘
```

---

## 파일 구조 및 역할

```
3d_clicker/
│
├── 🎨 UI Layer
│   └── app/ui.py                    # Gradio 인터페이스 (`create_ui`)
│       - gr.Blocks 기반 3페이지 단계별 레이아웃
│       - gr.Image, gr.Model3D 사용
│
├── 🔌 API / Generation Layer
│   └── app/api/
│       ├── __init__.py              # create_mesh_generator(): IMAGE_TO_3D_BACKEND 로 백엔드 선택
│       ├── openai_api.py            # OpenAIImageGenerator: gpt-image-2 이미지 생성
│       ├── lowpoly_api.py           # LowPolyModel: 로컬 로우폴리 3D 생성 (기본)
│       └── huggingface_api.py       # TripoSRModel: HF Space 호출 (선택, gradio-client 필요)
│
├── ⚙️ Processing & Core Layer
│   └── app/utils/
│       ├── config.py                # AppConfig: 환경 변수, 로그 설정
│       ├── lowpoly_prep.py          # 실루엣 추출, 외곽선 단순화, 디테일 맵/특징점
│       └── trimesh_utils.py         # MeshProcessor
│           - 메시 로드/크기 보정
│           - merge_solid_mesh_with_base_cap: 정렬 + 결합 (direct / voxel)
│           - solidify_with_voxels: 복셀 일체화
│
├── 🚀 Application Entry
│   └── app/main_gradio.py           # ImageToGoodsApp (상태, 이벤트 핸들러, 다운로드 라우팅)
│
├── 🗂 Assets
│   └── app/assets/
│       ├── base_keycap.stl          # 결합용 키캡 하부
│       ├── base_keycap2.stl         # 키링용 하부 (다운로드 제공)
│       ├── examples/                # 매뉴얼 이미지
│       └── samples/                 # 샘플 이미지
│
├── 🐳 Deployment
│   ├── Dockerfile                   # HF Spaces 전용 Docker 빌드
│   ├── .dockerignore
│   └── .github/workflows/sync-to-hf.yml
│
└── 📦 Dependencies
    └── requirements.txt             # gradio, trimesh, numpy, scipy, scikit-image 등
```

---

## 설정값 요약 (AppConfig)

| 변수 | 기본값 | 역할 |
|------|--------|------|
| `OPENAI_API_KEY` | (필수) | 이미지 생성 |
| `IMAGE_TO_3D_BACKEND` | `lowpoly` | 3D 생성 백엔드 선택 |
| `MERGE_MODE` | `auto` | 결합 방식 (`auto` / `direct` / `voxel`) |
| `BASE_KEYCAP_MODEL_SOURCE` | `app/assets/base_keycap.stl` | 결합용 키캡 하부 |
| `TRIPOSR_SPACE_URL`, `HF_API_TOKEN` | - | `triposr` 백엔드 전용 |
| `LOG_LEVEL` | `INFO` | 로그 수준 |

---

## 설계 메모

- **로컬 로우폴리를 기본으로 한 이유**: 외부 Space(TripoSR 등)는 빌드 실패나 GPU 쿼터 때문에 자주 막혔습니다. 로컬 변환은 서버와 GPU 없이 동작합니다.
- **직접 결합을 기본으로 한 이유**: 복셀 일체화는 형상이 계단 모양이 되고 색과 디테일이 사라져 품질이 크게 떨어졌습니다. 닫힌 입체이면 그대로 합치는 편이 품질이 좋습니다. 단, 두 입체가 겹친 채 한 파일에 들어가므로 슬라이서가 겹침을 합쳐 준다는 가정이 필요합니다.
- **`gradio_client`는 지연 로딩**: `triposr` 백엔드를 고를 때만 불러옵니다.

