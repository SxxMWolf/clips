# Video Clips

영상 병합, AI 프롬프트 생성, AI 클립 생성 기능을 제공하는 웹 기반 도구입니다.

## 주요 기능

- ✅ **영상 병합**: 여러 영상을 하나로 병합 (드래그 앤 드롭 지원)
- ✅ **AI 프롬프트 생성**: 주제를 입력하면 바이럴 프롬프트, 훅, 해시태그 자동 생성
- ✅ **AI 클립 생성**: YouTube 영상에서 바이럴 잠재력이 높은 클립 자동 생성
- ✅ **웹 인터페이스**: 직관적인 웹 UI로 모든 기능 사용 가능

## 빠른 시작

### 1. 필수 요구사항

**FFmpeg 설치** (필수):
```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# https://ffmpeg.org/download.html 에서 다운로드
```

**Python 패키지 설치**:
```bash
cd video-merger
pip3 install -r requirements.txt

# Playwright 브라우저 설치 (AI 클립 기능 사용 시)
python3 -m playwright install chromium
```

### 2. 환경 변수 설정

```bash
# env.example을 복사하여 .env 파일 생성
cp env.example .env

# .env 파일 편집
nano .env
```

**필수 설정:**
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 서버 실행

```bash
cd video-merger
./start_servers.sh
```

또는 수동으로:
```bash
# 자동 시작 스크립트 (권장)
./start_servers.sh

# 또는 수동으로
# FastAPI 서버 (AI 클리핑, 포트 8000)
cd ai_clipping && python3 ai_clipping_api.py &

# Flask 웹 서버 (메인 UI, 포트 5001)
python3 app.py
```

브라우저에서 **http://localhost:5001** 접속

## 기능 상세

### 1. 영상 병합

- 드래그 앤 드롭으로 영상 파일 추가
- 드래그로 영상 순서 조정
- 각 영상에 상단 텍스트 오버레이 추가 (4초 동안 표시)
- 출력 비율 선택 (9:16, 16:9, 1:1)
- 키워드 기반 파일명 생성
- 원본 영상 비우기 기능

**사용 방법:**
1. "영상 병합" 페이지 접속
2. 영상 파일을 드래그 앤 드롭 또는 클릭하여 선택
3. 각 영상의 상단 텍스트 입력 (선택사항)
4. 출력 비율 선택
5. 키워드 입력 (선택사항)
6. "영상 병합 시작" 버튼 클릭

### 2. AI 프롬프트 생성

주제를 입력하면 AI가 다음을 자동 생성:
- **AI Video/Image Prompt**: 주제를 영어로 번역한 프롬프트
- **Hook Caption**: 댓글을 유도하는 훅 캡션
- **Viral Hashtags**: 바이럴 잠재력이 높은 해시태그 (15-25개)

**특징:**
- 주제에 따라 ASMR 또는 시네마틱 스타일 자동 선택
- 크레딧 멘트 자동 추가 (옵션)
- 필수 해시태그 자동 포함 (#fyp, #viral, #trending, #shorts, #foryou)

**사용 방법:**
1. "AI 프롬프트" 페이지 접속
2. 주제 입력 (예: "체리 캔디 슬라임")
3. "Generate Prompt" 버튼 클릭
4. 생성된 프롬프트, 캡션, 해시태그 복사

### 3. AI 클립 생성

YouTube 영상에서 바이럴 잠재력이 높은 클립을 자동으로 생성합니다.

**프로세스:**
1. YouTube 영상 다운로드 및 오디오 추출
2. Whisper STT로 영어 전사 (타임스탬프 포함)
3. GPT가 바이럴 구간 3개 선택 (겹치지 않게)
4. FFmpeg로 클립 생성 (4:5 비율, 1080x1350)
5. 자동 자막 생성 및 삽입
6. AI 제목 및 해시태그 생성

**사용 방법:**
1. "AI 클립" 페이지 접속
2. YouTube URL 입력
3. 프롬프트 입력 (선택사항)
4. "YouTube 영상 다운로드" 버튼 클릭
5. 전사 완료 후 "AI 클립 생성" 버튼 클릭
6. 생성된 클립 확인 및 다운로드

## 프로젝트 구조

```
clips/
├── README.md                    # 이 파일
└── video-merger/
    ├── app.py                   # Flask 웹 서버
    ├── start_servers.sh         # 서버 시작 스크립트
    ├── requirements.txt         # Python 패키지
    ├── env.example              # 환경 변수 템플릿
    ├── prompt/                  # 프롬프트 생성 기능
    │   └── prompt_generator.py # AI 프롬프트 생성
    ├── merge/                   # 영상 병합 기능
    │   └── merge.py            # 영상 병합 로직
    ├── ai_clipping/             # 자동 클립 생성 기능
    │   ├── ai_clipping_api.py  # FastAPI (AI 클리핑)
    │   ├── stt_service.py       # Whisper STT
    │   ├── clip_selector.py    # GPT 클립 선택
    │   ├── clip_generator.py   # FFmpeg 클립 생성
    │   └── caption_generator.py # AI 제목/해시태그 생성
    ├── templates/              # HTML 템플릿
    │   ├── base.html
    │   ├── index.html
    │   ├── merge.html
    │   ├── ai_prompt.html
    │   └── ai_clip.html
    ├── static/                 # 정적 파일
    │   ├── style.css
    │   ├── script.js
    │   └── ai_clip.js
    └── videos/                 # 영상 파일
        ├── raw/                # 원본 영상 (병합용)
        ├── final/              # 병합된 영상
        ├── downloads/          # 다운로드된 YouTube 영상
        └── clips/              # 생성된 AI 클립
```

## 디렉토리 설명

- `videos/raw/`: 병합할 원본 영상 파일
- `videos/final/`: 병합된 최종 영상 파일
- `videos/downloads/`: YouTube에서 다운로드한 영상
- `videos/clips/`: AI로 생성된 클립
- `transcripts/`: Whisper STT 결과 (JSON)

## 환경 변수

`.env` 파일에 다음 변수를 설정하세요:

```bash
# OpenAI API 키 (필수)
OPENAI_API_KEY=your_openai_api_key_here
```

## 기술 스택

- **Backend**: Flask (웹 서버), FastAPI (AI 클리핑 API)
- **Video Processing**: FFmpeg
- **AI/ML**: OpenAI GPT-4o-mini, Whisper
- **Frontend**: HTML, CSS, JavaScript
- **YouTube Download**: yt-dlp
- **Computer Vision**: OpenCV (얼굴 감지)

## 주의사항

1. **보안**: `.env` 파일은 절대 Git에 커밋하지 마세요
2. **FFmpeg**: 반드시 설치되어 있어야 합니다
3. **API 키**: OpenAI API 키가 필요합니다
4. **영상 형식**: MP4 파일만 지원됩니다
5. **언어**: AI 클립 기능은 영어 영상만 지원합니다

## 트러블슈팅

**FFmpeg 오류**:
- FFmpeg 설치 확인: `ffmpeg -version`
- 설치 방법: https://ffmpeg.org/download.html

**OpenAI API 오류**:
- API 키 확인: `.env` 파일에 `OPENAI_API_KEY` 설정 확인
- API 사용량 한도 확인

**서버 실행 오류**:
- 포트 충돌 확인: 5001, 8000 포트가 사용 중인지 확인
- Python 패키지 설치 확인: `pip3 install -r requirements.txt`

**영상 병합 실패**:
- 영상 파일 형식 확인 (MP4)
- FFmpeg 설치 확인
- 디스크 공간 확인

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.
