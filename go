#!/bin/bash

# 프로젝트 루트에서 실행되도록 이동
cd "$(dirname "$0")/video-merger"

echo "🚀 AI 클리핑 시스템 서버 시작"
echo "================================"

# 가상환경 확인 및 활성화
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "../.venv" ]; then
        source ../.venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
fi

# 포트 정리 함수
cleanup_ports() {
    local ports=("8000" "5001")
    for port in "${ports[@]}"; do
        pid=$(lsof -t -i:$port)
        if [ ! -z "$pid" ]; then
            echo "🧹 포트 $port 사용 중인 프로세스 ($pid) 종료..."
            kill -9 $pid 2>/dev/null
        fi
    done
}

# 기존 프로세스 정리
cleanup_ports

# FastAPI 서버 시작 (백그라운드)
echo "📡 FastAPI 서버 시작 (포트 8000)..."
# 로그를 파일로 리다이렉트하여 터미널을 깨끗하게 유지 (선택사항)
python3 ai_clipping/ai_clipping_api.py > /dev/null 2>&1 &
FASTAPI_PID=$!

# 잠시 대기
sleep 2

# Flask 서버 시작
echo "🌐 Flask 웹 서버 시작 (포트 5001)..."
echo "================================"
echo "브라우저: http://127.0.0.1:5001"
echo "================================"
echo "종료: Ctrl+C"

# 종료 시그널 처리
trap "kill $FASTAPI_PID 2>/dev/null; echo '🛑 서버 종료됨'; exit" INT TERM

python3 app.py

# 종료 처리 (app.py가 정상 종료된 경우)
kill $FASTAPI_PID 2>/dev/null
echo "🛑 서버 종료됨"
