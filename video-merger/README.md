# video-merger 🎬

여러 개의 짧은 AI 영상을 하나의 쇼츠 영상으로 병합하는 도구입니다.

## 📋 기능

- ✅ FFmpeg를 사용한 빠른 영상 병합 (재인코딩 없음)
- ✅ 파일명 순서대로 자동 정렬
- ✅ 세로 영상(9:16) 기준
- ✅ 크로스 플랫폼 지원 (Windows/Mac/Linux)

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
python merge.py
```

**결과**:
- 병합된 영상: `videos/final/short.mp4`

## 📁 디렉토리 구조

```
video-merger/
├── merge.py          # 병합 스크립트
├── README.md         # 이 파일
└── videos/
    ├── raw/          # 원본 영상들 (입력)
    └── final/        # 병합된 영상 (출력)
```

## 💡 사용 예시

```bash
# 1. 원본 영상 준비
cp runway_video_1.mp4 videos/raw/01.mp4
cp runway_video_2.mp4 videos/raw/02.mp4
cp runway_video_3.mp4 videos/raw/03.mp4

# 2. 병합 실행
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

## 📝 라이선스

이 프로젝트는 교육 및 개인 사용 목적으로 제공됩니다.

