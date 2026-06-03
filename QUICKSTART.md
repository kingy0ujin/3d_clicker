# 🚀 빠른 시작 가이드 (Quick Start)

## 📋 사전 준비

### 1. API 키 발급 (5분)

**OpenAI API Key (필수):**
1. https://platform.openai.com/api-keys 방문
2. **Create new secret key** 클릭
3. 키 복사 후 저장

**Hugging Face Token (선택사항):**
- 공개 HF Spaces를 사용하므로 토큰 없이도 실행 가능
- 필요한 경우: https://huggingface.co/settings/tokens에서 발급

### 2. 환경 설정 (1분)

`.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 편집:
```
OPENAI_API_KEY=sk_your_key_here
# HF_API_TOKEN은 선택사항
# HF_API_TOKEN=hf_your_token_here
# BASE_KEYCAP_MODEL_SOURCE=https://your-server/path/to/base_keycap.glb
```

---

## ⚡ 실행 방법

### 1️⃣ 가상환경 생성 (첫 실행 시에만)

```bash
python -m venv venv
```

### 2️⃣ 가상환경 활성화

**Windows:**
```bash
venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3️⃣ 의존성 설치 (첫 실행 시에만)

```bash
pip install -r requirements.txt
```

### 4️⃣ 앱 실행

```bash
# Windows (venv 활성화 후)
venv\Scripts\python.exe -m app.main_gradio

# 또는
python -m app.main_gradio
```

✅ 앱이 시작되면 브라우저에서 **http://localhost:7860** 열기

---

---

## 🎯 사용 방법 (2분)

### 예시: 귀여운 강아지 키캡/키캡 키링 만들기

1. **아이디어 입력**: "귀여운 강아지"
2. **이미지 생성 클릭** → 30초 대기
3. **3D 메시 생성 클릭** → 50초 대기
4. **키캡 하단부와 결합 클릭** → 30초 대기
6. **obj, glb 다운로드**: 완성된 커스텀 키캡 파일 다운로드
7. **3D 프린팅**: 각 3D 파일 출력
8. **조립**: 키보드에 결합/ 기계식 스위치(키축) 끼운 후 상하부 결합

---

## 📊 처리 시간

| 단계 | 소요 시간 |
|------|---------|
| 이미지 생성 | 30초 |
| 3D 메시 생성 | 50초 |
| 메시 처리 | 30초 |
| **총 시간** | **1분 50초** |

---

## 🔍 API 상태 확인

```bash
# API 연결 점검은 앱 실행 후 로그에서 확인하거나, 필요 시 별도 스크립트를 만드세요.
```

---

## 💰 예상 비용 

| 서비스 | 비용 |
|--------|------|
| OpenAI gpt-image-2 (hd) | $5.00 |
| Hugging Face | 무료 |
| **합계** | **$4/월** |

---

## ❓ FAQ

**Q: 이미지가 생성되지 않아요**
→ `.env` 파일의 `OPENAI_API_KEY` 확인. 유효한 API 키가 필요합니다.

**Q: 3D 메시가 로드되지 않아요**
→ InstantMesh 모델이 처음 로드될 때 시간이 걸립니다. 재시도하면 빠릅니다.

**Q: STL 파일이 손상되었어요**
→ 3D 프린팅 소프트웨어(Cura, PrusaSlicer)에서 자동 수리 활성화

**Q: 스위치 홈이 너무 작아요**
→ `app/utils/trimesh_utils.py`에서 `SWITCH_CAVITY_WIDTH` 값 조정

---

## 📚 상세 문서

- [README.md](README.md) - 프로젝트 전체 설명
- [OpenAI API 문서](https://platform.openai.com/docs/)
- [HF InstantMesh](https://huggingface.co/TencentARC/InstantMesh)
- [Trimesh 문서](https://trimesh.org/)

---

## 🐳 Docker 배포 (HF Spaces)

```bash
# HF Spaces에서 "Docker 모드" 공간 생성 후:
git clone https://huggingface.co/spaces/your-user/your-space
cd your-space

# 파일 복사
cp -r /path/to/aiweb_clicker/* .

# 배포
git add .
git commit -m "Deploy Image-to-Goods"
git push
```

---

**다음 단계:** `.env` 파일을 만들고 앱을 실행하세요: `python -m app.main_gradio` 🎉
