"""
STT 서비스 (Whisper)
영어 오디오를 텍스트로 변환하고 타임스탬프를 제공합니다.
"""

import logging
from pathlib import Path
import whisper

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-Text 서비스 (Whisper)"""
    
    def __init__(self, model_size: str = "base"):
        """
        Args:
            model_size: whisper 모델 크기 (tiny, base, small, medium, large)
        """
        logger.info(f"Whisper 모델 로딩: {model_size}")
        self.model = whisper.load_model(model_size)
        logger.info("Whisper 모델 로딩 완료")
    
    def transcribe(self, audio_path: Path) -> list:
        """
        오디오를 텍스트로 변환하고 타임스탬프를 반환합니다.
        
        Args:
            audio_path: WAV 오디오 파일 경로
            
        Returns:
            [
                {
                    "start": 12.3,
                    "end": 18.9,
                    "text": "This is where everything changes."
                },
                ...
            ]
        """
        logger.info(f"STT 시작: {audio_path}")
        
        # Whisper로 전사
        result = self.model.transcribe(
            str(audio_path),
            language="en",
            word_timestamps=True
        )
        
        # 문장 단위로 그룹화
        segments = []
        current_segment = {
            "start": None,
            "end": None,
            "text": ""
        }
        
        for segment in result["segments"]:
            # 문장 끝 감지 (마침표, 느낌표, 물음표)
            text = segment["text"].strip()
            if not text:
                continue
            
            if current_segment["start"] is None:
                current_segment["start"] = segment["start"]
            
            current_segment["end"] = segment["end"]
            current_segment["text"] += " " + text if current_segment["text"] else text
            
            # 문장 끝 감지
            if text.endswith(('.', '!', '?')):
                segments.append({
                    "start": round(current_segment["start"], 2),
                    "end": round(current_segment["end"], 2),
                    "text": current_segment["text"].strip()
                })
                current_segment = {
                    "start": None,
                    "end": None,
                    "text": ""
                }
        
        # 마지막 세그먼트 추가
        if current_segment["start"] is not None:
            segments.append({
                "start": round(current_segment["start"], 2),
                "end": round(current_segment["end"], 2),
                "text": current_segment["text"].strip()
            })
        
        logger.info(f"STT 완료: {len(segments)}개 세그먼트")
        return segments

