# Python 3.9 베이스 이미지 사용
FROM python:3.9-slim

# 시스템 의존성 설치 (FFmpeg 필수)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 전체 복사
COPY . .

# go 스크립트 실행 권한 부여
RUN chmod +x go

# 포트 노출 (Flask: 5001, FastAPI: 8000)
EXPOSE 5001 8000

# 프로젝트 루트에서 go 스크립트 실행
# go 스크립트가 내부적으로 video-merger 폴더로 이동하여 실행함
CMD ["./go"]
