"""
AI 기반 비디오 클리핑 FastAPI 서버
YouTube URL에서 바이럴 클립을 자동으로 생성합니다.
"""

import os
import uuid
import json
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from stt_service import STTService
from clip_selector import ClipSelector
from clip_generator import ClipGenerator
from caption_generator import CaptionGenerator

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Video Clipping API", version="1.0.0")

# CORS 설정 (Flask 앱과 통신)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5001", "http://127.0.0.1:5001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 설정
VIDEOS_DIR = Path("videos")
DOWNLOADS_DIR = VIDEOS_DIR / "downloads"
CLIPS_DIR = VIDEOS_DIR / "clips"
TRANSCRIPTS_DIR = Path("transcripts")

# 디렉토리 생성
for dir_path in [DOWNLOADS_DIR, CLIPS_DIR, TRANSCRIPTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# Pydantic 모델
class YouTubeImportRequest(BaseModel):
    url: HttpUrl
    prompt: Optional[str] = "Find the most engaging and viral moments"


class ClipGenerationRequest(BaseModel):
    video_id: str
    prompt: Optional[str] = "Find the most engaging and viral moments"


class ClipSegment(BaseModel):
    start: float
    end: float
    hook: str
    confidence: float


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


# 서비스 인스턴스
stt_service = STTService()
clip_selector = ClipSelector()
clip_generator = ClipGenerator()
caption_generator = CaptionGenerator()


@app.get("/")
def root():
    """API 상태 확인"""
    return {"status": "ok", "service": "AI Video Clipping API"}


@app.post("/api/video/import/youtube")
async def import_youtube_video(request: YouTubeImportRequest, background_tasks: BackgroundTasks):
    """
    1단계: YouTube 영상 다운로드 & 오디오 분리
    """
    try:
        video_id = str(uuid.uuid4())
        logger.info(f"YouTube 다운로드 시작: {request.url} (video_id: {video_id})")
        
        # 비동기로 다운로드 및 처리
        background_tasks.add_task(
            download_and_process_video,
            str(request.url),
            video_id
        )
        
        return {
            "success": True,
            "video_id": video_id,
            "message": "다운로드가 시작되었습니다. /api/video/status/{video_id}에서 상태를 확인하세요."
        }
    except Exception as e:
        logger.error(f"YouTube 다운로드 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/status/{video_id}")
def get_video_status(video_id: str):
    """비디오 처리 상태 확인"""
    video_file = DOWNLOADS_DIR / f"{video_id}.mp4"
    audio_file = DOWNLOADS_DIR / f"{video_id}.wav"
    transcript_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    
    status = {
        "video_id": video_id,
        "downloaded": video_file.exists(),
        "audio_extracted": audio_file.exists(),
        "transcribed": transcript_file.exists(),
    }
    
    if video_file.exists():
        import subprocess
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(video_file)],
                capture_output=True,
                text=True,
                check=True
            )
            status["duration"] = float(result.stdout.strip())
        except:
            pass
    
    if transcript_file.exists():
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
                status["transcript_segments"] = len(transcript)
        except:
            pass
    
    return status


@app.post("/api/video/generate-clips")
async def generate_clips(request: ClipGenerationRequest, background_tasks: BackgroundTasks):
    """
    3-7단계: 클립 생성 파이프라인
    STT → GPT 클립 선택 → FFmpeg 클리핑 → 자막 생성 → 제목/해시태그 생성
    """
    try:
        video_id = request.video_id
        logger.info(f"클립 생성 시작: {video_id}")
        
        # 비동기로 클립 생성
        background_tasks.add_task(
            generate_clips_pipeline,
            video_id,
            request.prompt
        )
        
        return {
            "success": True,
            "video_id": video_id,
            "message": "클립 생성이 시작되었습니다. /api/clips/{video_id}에서 결과를 확인하세요."
        }
    except Exception as e:
        logger.error(f"클립 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clips/{video_id}")
def get_clips(video_id: str):
    """생성된 클립 목록 조회"""
    clips_dir = CLIPS_DIR / video_id
    metadata_file = clips_dir / "metadata.json"
    
    if not clips_dir.exists():
        return {
            "video_id": video_id,
            "clips": [],
            "status": "not_found"
        }
    
    clips = []
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                clips = metadata.get("clips", [])
        except Exception as e:
            logger.error(f"메타데이터 읽기 오류: {e}")
    
    # 실제 파일 존재 여부 확인
    for clip in clips:
        clip_file = clips_dir / clip["filename"]
        clip["file_exists"] = clip_file.exists()
        clip["file_path"] = f"/api/clips/{video_id}/file/{clip['filename']}"
    
    return {
        "video_id": video_id,
        "clips": clips,
        "status": "ready" if clips else "processing"
    }


@app.get("/api/clips/{video_id}/file/{filename}")
def get_clip_file(video_id: str, filename: str):
    """클립 파일 다운로드"""
    from fastapi.responses import FileResponse
    clip_file = CLIPS_DIR / video_id / filename
    
    if not clip_file.exists():
        raise HTTPException(status_code=404, detail="클립 파일을 찾을 수 없습니다.")
    
    return FileResponse(
        clip_file,
        media_type="video/mp4",
        filename=filename
    )


# 백그라운드 작업 함수들
def download_and_process_video(url: str, video_id: str):
    """YouTube 다운로드 및 오디오 분리"""
    try:
        import yt_dlp
        import subprocess
        
        video_file_base = DOWNLOADS_DIR / video_id
        audio_file = DOWNLOADS_DIR / f"{video_id}.wav"
        
        # YouTube 다운로드 (403 오류 방지를 위한 옵션 추가)
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': str(video_file_base) + '.%(ext)s',  # 확장자 포함
            'quiet': False,
            'no_warnings': False,
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            'nocheckcertificate': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as download_error:
            # 첫 번째 시도 실패 시 다른 옵션으로 재시도
            logger.warning(f"첫 번째 다운로드 시도 실패: {download_error}")
            logger.info("대체 옵션으로 재시도 중...")
            
            ydl_opts_retry = {
                'format': 'worst[ext=mp4]/worst',
                'outtmpl': str(video_file_base) + '.%(ext)s',  # 확장자 포함
                'quiet': False,
                'no_warnings': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios', 'android'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_retry) as ydl:
                ydl.download([url])
        
        # 다운로드된 실제 파일 찾기 (확장자 자동 감지)
        video_file = None
        possible_extensions = ['.mp4', '.mkv', '.webm', '.m4a']
        for ext in possible_extensions:
            candidate = video_file_base.with_suffix(ext)
            if candidate.exists():
                video_file = candidate
                break
        
        # 확장자 없이 저장된 경우도 확인
        if video_file is None and video_file_base.exists():
            video_file = video_file_base
        
        if video_file is None or not video_file.exists():
            raise FileNotFoundError(f"다운로드된 비디오 파일을 찾을 수 없습니다: {video_file_base}")
        
        logger.info(f"다운로드된 파일: {video_file}")
        
        # 오디오 추출 (16kHz, mono)
        logger.info(f"오디오 추출 중: {video_id}")
        result = subprocess.run([
            'ffmpeg', '-i', str(video_file),
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(audio_file)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg 오류: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        
        logger.info(f"다운로드 완료: {video_id}")
        
    except Exception as e:
        logger.error(f"다운로드/처리 오류: {e}")
        raise


def generate_clips_pipeline(video_id: str, prompt: str):
    """전체 클립 생성 파이프라인"""
    try:
        # 다운로드된 실제 비디오 파일 찾기
        video_file_base = DOWNLOADS_DIR / video_id
        video_file = None
        possible_extensions = ['.mp4', '.mkv', '.webm', '.m4a']
        for ext in possible_extensions:
            candidate = video_file_base.with_suffix(ext)
            if candidate.exists():
                video_file = candidate
                break
        
        # 확장자 없이 저장된 경우도 확인
        if video_file is None and video_file_base.exists():
            video_file = video_file_base
        
        if video_file is None or not video_file.exists():
            raise FileNotFoundError(f"다운로드된 비디오 파일을 찾을 수 없습니다: {video_id}")
        
        audio_file = DOWNLOADS_DIR / f"{video_id}.wav"
        transcript_file = TRANSCRIPTS_DIR / f"{video_id}.json"
        
        # 2단계: STT
        if not transcript_file.exists():
            logger.info(f"STT 시작: {video_id}")
            transcript = stt_service.transcribe(audio_file)
            with open(transcript_file, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
        else:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
        
        # 3단계: GPT 클립 선택
        logger.info(f"클립 선택 시작: {video_id}")
        selected_clips = clip_selector.select_clips(transcript, prompt)
        
        # 4-5단계: FFmpeg 클리핑 및 자막 생성
        logger.info(f"클립 생성 시작: {video_id}")
        clips_dir = CLIPS_DIR / video_id
        clips_dir.mkdir(parents=True, exist_ok=True)
        
        generated_clips = []
        for i, clip_segment in enumerate(selected_clips, 1):
            clip_info = clip_generator.generate_clip(
                video_file,
                clip_segment,
                transcript,
                clips_dir,
                f"{video_id}_clip_{i:02d}.mp4"
            )
            
            # 7단계: 제목/해시태그 생성
            clip_text = " ".join([
                seg["text"] for seg in transcript
                if clip_segment["start"] <= seg["start"] < clip_segment["end"]
            ])
            
            caption = caption_generator.generate_caption(
                clip_text,
                clip_segment["hook"]
            )
            
            clip_info.update({
                "title": caption["title"],
                "hashtags": caption["hashtags"],
                "description": caption.get("description", "")
            })
            
            generated_clips.append(clip_info)
        
        # 메타데이터 저장
        metadata = {
            "video_id": video_id,
            "prompt": prompt,
            "clips": generated_clips
        }
        
        metadata_file = clips_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"클립 생성 완료: {video_id} ({len(generated_clips)}개)")
        
    except Exception as e:
        logger.error(f"클립 생성 파이프라인 오류: {e}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

