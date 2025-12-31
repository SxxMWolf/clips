#!/bin/bash

# AI 클리핑 시스템 서버 시작 스크립트

echo "🚀 AI 클리핑 시스템 서버 시작"
echo "================================"

# FastAPI 서버 시작 (백그라운드)
echo "📡 FastAPI 서버 시작 (포트 8000)..."
python3 ai_clipping_api.py &
FASTAPI_PID=$!

# 잠시 대기
sleep 2

# Flask 서버 시작
echo "🌐 Flask 웹 서버 시작 (포트 5001)..."
echo "================================"
echo "브라우저에서 http://localhost:5001 접속"
echo "================================"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo ""

# 종료 시 FastAPI 프로세스도 종료
trap "kill $FASTAPI_PID 2>/dev/null; exit" INT TERM

python3 app.py

# 종료 처리
kill $FASTAPI_PID 2>/dev/null

