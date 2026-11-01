# 🚀 빠른 시작 가이드 (Quick Start)

## 📋 사전 준비

### 1. OpenAI API 키 발급 (필수)

1. https://platform.openai.com/api-keys 방문
2. **Create new secret key** 클릭
3. 키를 복사해 둡니다.

이미지 생성에만 쓰입니다. 이미지를 직접 업로드하거나 샘플을 쓰더라도 앱 시작 시 키가 설정돼 있어야 합니다.

### 2. 환경 설정

프로젝트 루트에 `.env` 파일을 만들고 키를 넣습니다.

```
OPENAI_API_KEY=sk_your_key_here
```

3D 변환은 내 PC에서 실행되므로 Hugging Face 토큰이나 GPU는 필요 없습니다.
(선택 설정은 [README.md](README.md)의 환경 변수 표를 참고하세요.)

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
python -m app.main_gradio
```

Windows에서는 `run.bat`을 실행해도 됩니다.
앱이 시작되면 브라우저에서 **http://localhost:7860** 을 엽니다.

---

## 🎯 사용 방법

### 예시: 귀여운 강아지 키캡 만들기

1. **Page 1**: "귀여운 강아지"를 입력하고 **이미지 생성**을 누릅니다. (이미지 업로드나 샘플 선택도 가능)
2. **Page 2**: **3D 메시 빌드**를 누릅니다. 해상도 슬라이더로 삼각형 수를 조절합니다.
3. **Page 3**: 축 방향 프리셋을 고르고 **하부와 결합**을 누릅니다.
4. **다운로드**: 최종 GLB/OBJ를 내려받습니다. 키링용 하부 STL도 받을 수 있습니다.
5. **3D 프린팅**: 파일을 출력합니다.
6. **조립**: 기계식 스위치(키축)를 끼우고 상하부를 결합합니다.

### 잘 나오게 하는 팁
- 배경이 투명한 PNG나, 배경이 단색인 이미지를 쓰면 실루엣이 정확합니다.
- 팔이 몸에 붙은 구조처럼 여러 덩어리인 이미지는 가장 큰 덩어리 하나만 사용합니다.
- 결합 결과의 방향이 어색하면 **축 방향 프리셋**을 바꿔 보세요.

---

## 🔍 문제 해결

| 증상 | 확인할 것 |
|------|-----------|
| 시작하자마자 종료 | `.env`에 `OPENAI_API_KEY`가 있는지 확인 |
| "이미지에서 물체를 찾지 못했습니다" | 배경이 복잡하거나 물체와 배경 색이 비슷함 → 투명 PNG 사용 |
| 결합 실패 | `app/assets/base_keycap.stl`이 있는지, `BASE_KEYCAP_MODEL_SOURCE` 경로가 맞는지 확인 |
| 결합 결과가 계단 모양에 색이 없음 | `MERGE_MODE=voxel`이거나 캐릭터가 닫힌 입체가 아닌 경우 → `MERGE_MODE=auto` 확인 |

---

## 🐳 Docker 배포 (HF Spaces)

```bash
docker build -t image-to-goods:latest .
docker run -d -p 7860:7860 --env-file .env image-to-goods:latest
```

HF Space에서는 `.github/workflows/sync-to-hf.yml`이 main에 push할 때 자동으로 동기화합니다.

---

## 📚 상세 문서

- [README.md](README.md) - 프로젝트 전체 설명
- [ARCHITECTURE.md](ARCHITECTURE.md) - 구조와 처리 흐름
- [Trimesh 문서](https://trimesh.org/)

