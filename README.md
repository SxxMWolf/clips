# video-merger 🎬

여러 개의 짧은 AI 영상을 하나의 쇼츠 영상으로 병합하는 도구입니다.

## 📋 기능

- ✅ FFmpeg를 사용한 빠른 영상 병합 (재인코딩 없음)
- ✅ 파일명 순서대로 자동 정렬
- ✅ 세로 영상(9:16) 기준
- ✅ 크로스 플랫폼 지원 (Windows/Mac/Linux)
- ✅ **YouTube, TikTok, Instagram 자동 업로드**
- ✅ **스케줄링을 통한 자동 업로드**

## 🚀 빠른 시작

### 1. FFmpeg 설치

**Mac (Homebrew)**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows**:
https://ffmpeg.org/download.html 에서 다운로드

### 2. 영상 준비

```bash
# videos/raw/ 폴더 생성
mkdir -p videos/raw videos/final

# 원본 영상들을 videos/raw/에 배치
cp your_videos/*.mp4 videos/raw/
```

**파일명 규칙**:
- 숫자 순서: `01.mp4`, `02.mp4`, `03.mp4` (권장)
- 알파벳 순서: `a.mp4`, `b.mp4`, `c.mp4`
- 자동으로 정렬되어 병합됩니다

### 3. 병합 실행

```bash
cd video-merger
python3 merge.py
```

**결과**:
- 병합된 영상: `videos/final/short.mp4`

## 📁 디렉토리 구조

```
clips/
├── README.md          # 이 파일
└── video-merger/
    ├── merge.py       # 병합 스크립트
    ├── README.md      # 상세 사용 가이드
    ├── requirements.txt
    └── videos/
        ├── raw/       # 원본 영상들 (입력)
        └── final/     # 병합된 영상 (출력)
```

## 💡 사용 예시

```bash
# 1. 원본 영상 준비
cp runway_video_1.mp4 video-merger/videos/raw/01.mp4
cp runway_video_2.mp4 video-merger/videos/raw/02.mp4
cp runway_video_3.mp4 video-merger/videos/raw/03.mp4

# 2. 병합 실행
cd video-merger
python3 merge.py

# 3. 결과 확인
ls -lh videos/final/short.mp4
```

## ⚙️ 동작 원리

- FFmpeg concat demuxer 사용 (`-c copy`)
- 재인코딩 없이 스트림 복사 (매우 빠름)
- 파일명 순서대로 정렬 (`sorted()`)
- 임시 concat 파일 자동 생성 및 삭제

## ⚠️ 주의사항

1. **영상 형식**: 모든 원본 영상이 같은 코덱/해상도/프레임레이트여야 함
2. **파일 형식**: MP4 포맷 사용 권장
3. **FFmpeg**: 반드시 설치되어 있어야 함

## 🔧 트러블슈팅

**FFmpeg가 설치되어 있지 않습니다**:
- FFmpeg 설치 확인: `ffmpeg -version`
- 설치 방법: https://ffmpeg.org/download.html

**코덱이 다른 영상들을 병합할 수 없습니다**:
- 모든 원본 영상이 같은 코덱/해상도/프레임레이트인지 확인
- 필요시 영상을 먼저 재인코딩하여 형식 통일

---

## 🚀 자동 업로드 기능

병합된 영상을 YouTube, TikTok, Instagram에 자동으로 업로드할 수 있습니다.

### 1. 패키지 설치

```bash
cd video-merger
pip3 install -r requirements.txt
python3 -m playwright install chromium  # Playwright 브라우저 설치
```

### 2. 환경 변수 설정

```bash
# env.example을 복사하여 .env 파일 생성
cp env.example .env

# .env 파일을 편집하여 로그인 정보 입력
nano .env
```

**필수 설정:**
- YouTube: Google Cloud Console에서 OAuth 2.0 클라이언트 ID 다운로드 → `credentials.json`으로 저장
- TikTok: `TIKTOK_EMAIL`, `TIKTOK_PASSWORD` 설정
- Instagram: `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` 설정

### 3. YouTube 업로드 (공식 API)

```bash
python3 upload_youtube.py
```

**설정 방법:**
1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 접속
2. 프로젝트 생성 → YouTube Data API v3 활성화
3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. `credentials.json` 다운로드 → `video-merger/` 폴더에 저장
5. 첫 실행 시 브라우저에서 인증 완료

### 4. TikTok 업로드 (브라우저 자동화)

```bash
python3 upload_tiktok.py
```

**주의사항:**
- Playwright를 사용한 브라우저 자동화
- `.env` 파일에 `TIKTOK_EMAIL`, `TIKTOK_PASSWORD` 설정 필요
- `TIKTOK_HEADLESS=false`로 설정하면 브라우저 창이 보여 디버깅 가능

### 5. Instagram 업로드 (브라우저 자동화)

```bash
python3 upload_instagram.py
```

**주의사항:**
- Playwright를 사용한 브라우저 자동화
- `.env` 파일에 `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` 설정 필요
- `INSTAGRAM_HEADLESS=false`로 설정하면 브라우저 창이 보여 디버깅 가능

### 6. 스케줄러 실행

지정된 시간에 자동으로 업로드:

```bash
# 스케줄러 실행 (백그라운드)
python3 scheduler.py

# 즉시 모든 플랫폼에 업로드
python3 scheduler.py now
```

**기본 스케줄:**
- YouTube: 오전 11시, 오후 6시
- TikTok: 오후 7시
- Instagram: 오후 6시

`.env` 파일에서 `*_UPLOAD_TIME` 변수로 시간 변경 가능

### 7. 메타데이터 설정

`metadata.json` 파일을 수정하여 제목, 설명, 태그 등을 설정:

```json
{
  "title": "나만의 쇼츠 영상",
  "description": "#shorts #쇼츠\n\n재미있는 영상입니다!",
  "tags": ["shorts", "쇼츠", "video"],
  "category": "22",
  "privacy": "public"
}
```

## 📁 업데이트된 디렉토리 구조

```
clips/
├── README.md              # 이 파일
└── video-merger/
    ├── app.py             # 웹 서버 (Flask)
    ├── merge.py           # 병합 스크립트
    ├── upload_youtube.py  # YouTube 업로드
    ├── upload_tiktok.py   # TikTok 업로드
    ├── upload_instagram.py # Instagram 업로드
    ├── scheduler.py       # 자동 스케줄러
    ├── metadata.json      # 업로드 메타데이터
    ├── env.example        # 환경 변수 템플릿
    ├── requirements.txt   # Python 패키지
    ├── templates/         # HTML 템플릿
    │   └── index.html
    ├── static/            # 정적 파일 (CSS, JS)
    │   ├── style.css
    │   └── script.js
    └── videos/
        ├── raw/           # 원본 영상들 (입력)
        └── final/         # 병합된 영상 (출력)
```

## ⚠️ 자동 업로드 주의사항

1. **YouTube API**: Google Cloud Console에서 프로젝트 생성 및 API 활성화 필요
2. **TikTok/Instagram**: 브라우저 자동화 사용으로 인해 플랫폼 정책 변경 시 동작하지 않을 수 있음
3. **보안**: `.env` 파일에 로그인 정보가 포함되므로 Git에 커밋하지 마세요
4. **스케줄러**: 24시간 실행하려면 서버나 클라우드 인스턴스 필요

---

## 🌐 웹 인터페이스

브라우저에서 쉽게 사용할 수 있는 웹 대시보드를 제공합니다.

### 1. 웹 서버 실행

```bash
cd video-merger
python3 app.py
```

브라우저에서 **http://localhost:5001** 접속

### 2. 주요 기능

#### 📊 대시보드
- 원본 영상 목록 확인
- 병합된 영상 상태 및 미리보기
- 스케줄러 실행 상태

#### 🔀 영상 병합
- `videos/raw/` 폴더의 영상들을 하나로 병합
- 실시간 상태 업데이트

#### 📤 플랫폼별 업로드
- **YouTube**: 공식 API를 통한 업로드
- **TikTok**: 브라우저 자동화 업로드
- **Instagram**: 브라우저 자동화 업로드
- **모두 업로드**: 한 번에 모든 플랫폼에 업로드

#### ⏰ 스케줄러
- 지정된 시간에 자동 업로드
- 시작/중지 제어

#### 📝 메타데이터 편집
- 제목, 설명, 태그 설정
- 공개 설정 (공개/링크로만/비공개)
- YouTube 업로드 시 사용

### 3. 웹 인터페이스 특징

- ✅ **직관적인 UI**: 모던하고 사용하기 쉬운 디자인
- ✅ **실시간 업데이트**: 5초마다 자동으로 상태 갱신
- ✅ **반응형 디자인**: 모바일/태블릿/데스크톱 지원
- ✅ **비동기 처리**: 업로드 작업이 백그라운드에서 실행
- ✅ **알림 시스템**: 작업 완료/오류 시 토스트 알림

### 4. 웹 서버 설정

기본 포트는 5001번입니다 (포트 5000은 macOS ControlCenter가 사용 중). 다른 포트를 사용하려면 `app.py` 파일을 수정하세요:

```python
app.run(debug=True, host='0.0.0.0', port=8080)  # 포트 변경
```

**원격 접속 허용**: `host='0.0.0.0'`으로 설정하면 같은 네트워크의 다른 기기에서도 접속 가능합니다.

**프로덕션 환경**: `debug=False`로 설정하여 보안을 강화하세요.

---

## 🤖 AI 클리핑 시스템 (Opus Clip 스타일)

YouTube 영상에서 바이럴 잠재력이 높은 클립을 자동으로 생성합니다.

### 1. 시스템 아키텍처

```
YouTube URL → 다운로드 → STT (Whisper) → GPT 클립 선택 → FFmpeg 클리핑 → 자막 생성 → 업로드
```

### 2. 시작하기

#### 패키지 설치
```bash
cd video-merger
pip3 install -r requirements.txt

# Whisper 모델 다운로드 (자동)
# Playwright 브라우저 설치
playwright install chromium
```

#### 환경 변수 설정
`.env` 파일에 OpenAI API 키 추가:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

#### 서버 실행

**방법 1: 자동 시작 스크립트 (권장)**
```bash
./start_servers.sh
# FastAPI (8000)와 Flask (5001) 서버를 모두 시작
```

**방법 2: 수동 시작**

**1. FastAPI 서버 (AI 클리핑)**
```bash
python3 ai_clipping_api.py
# http://localhost:8000 에서 실행
```

**2. Flask 웹 서버 (메인 UI)**
```bash
python3 app.py
# http://localhost:5001 에서 실행
```

> **참고**: 두 서버를 모두 실행해야 AI 클리핑 기능이 작동합니다.

### 3. 사용 방법

#### 웹 UI에서 사용

1. **YouTube URL 입력**
   - 웹 UI의 "AI 클리핑" 섹션에서 YouTube URL 입력
   - 프롬프트 입력 (예: "Find the most engaging and viral moments")

2. **영상 다운로드**
   - "YouTube 영상 다운로드" 버튼 클릭
   - 다운로드 및 오디오 추출 진행 상황 확인

3. **AI 클립 생성**
   - 전사 완료 후 "AI 클립 생성" 버튼 클릭
   - GPT가 바이럴 잠재력이 높은 구간 2-5개 선택
   - 각 클립은 15-45초, 9:16 세로 형식

4. **클립 확인 및 업로드**
   - 생성된 클립 미리보기
   - 각 클립의 제목, 해시태그, 신뢰도 확인
   - YouTube, TikTok, Instagram에 개별 업로드

#### API 직접 사용

```bash
# 1. YouTube 영상 다운로드
curl -X POST http://localhost:8000/api/video/import/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=...", "prompt": "Find shocking moments"}'

# 2. 상태 확인
curl http://localhost:8000/api/video/status/{video_id}

# 3. 클립 생성
curl -X POST http://localhost:8000/api/video/generate-clips \
  -H "Content-Type: application/json" \
  -d '{"video_id": "...", "prompt": "..."}'

# 4. 클립 목록 조회
curl http://localhost:8000/api/clips/{video_id}
```

### 4. 주요 기능

#### 🎯 GPT 기반 클립 선택
- 감정적 강도 분석
- 훅 강도 평가
- 참여 잠재력 예측
- 호기심 갭 식별
- 논란/놀라운 순간 감지

#### ✂️ 자동 클리핑
- FFmpeg를 사용한 빠른 클리핑 (재인코딩 최소화)
- 9:16 세로 형식 자동 변환
- 스마트 크롭 (중앙 또는 중요 영역)

#### 📝 자동 자막
- Whisper STT 결과 기반
- Shorts 스타일 자막 (큰 글씨, 중앙 하단)
- 키워드 하이라이트

#### 🏷️ AI 제목/해시태그
- 바이럴 잠재력 높은 제목 생성
- 15-25개 해시태그 자동 생성
- 플랫폼별 최적화

### 5. 생성된 파일 구조

```
videos/
├── downloads/          # 다운로드된 원본 영상
│   ├── {video_id}.mp4
│   └── {video_id}.wav
├── clips/              # 생성된 클립
│   └── {video_id}/
│       ├── {video_id}_clip_01.mp4
│       ├── {video_id}_clip_02.mp4
│       └── metadata.json
└── transcripts/        # STT 결과
    └── {video_id}.json
```

### 6. 성능 및 제한사항

- **STT**: Whisper base 모델 사용 (더 빠른 처리를 위해)
- **클립 길이**: 15-45초 (최적 범위)
- **비디오 형식**: MP4 (H.264)
- **해상도**: 1080x1920 (9:16)
- **언어**: 영어만 지원

### 7. 트러블슈팅

**Whisper 모델 다운로드 실패**:
- 인터넷 연결 확인
- 수동 다운로드: `whisper.load_model("base")` 실행

**GPT API 오류**:
- OpenAI API 키 확인
- API 사용량 한도 확인

**FFmpeg 오류**:
- FFmpeg 설치 확인: `ffmpeg -version`
- 비디오 코덱 호환성 확인

**클립이 생성되지 않음**:
- 비디오 길이 확인 (최소 15초 필요)
- STT 결과 확인 (`transcripts/` 폴더)
