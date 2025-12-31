"""
FFmpeg 클립 생성 서비스
선택된 구간을 4:5 비율(1080×1350)로 클리핑하고 자막을 추가합니다.
얼굴 감지 기반 스마트 크롭 지원.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    FACE_DETECTION_AVAILABLE = True
except ImportError:
    FACE_DETECTION_AVAILABLE = False
    logger.warning("OpenCV not available. Face detection disabled. Install with: pip install opencv-python")


class ClipGenerator:
    """FFmpeg를 사용한 클립 생성 서비스"""
    
    def __init__(self):
        """얼굴 감지기 초기화"""
        self.face_cascade = None
        if FACE_DETECTION_AVAILABLE:
            try:
                # OpenCV 얼굴 감지기 로드
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                if self.face_cascade.empty():
                    logger.warning("얼굴 감지 모델 로드 실패. 중앙 크롭 사용.")
                    self.face_cascade = None
                else:
                    logger.info("얼굴 감지 모델 로드 완료")
            except Exception as e:
                logger.warning(f"얼굴 감지 초기화 실패: {e}. 중앙 크롭 사용.")
                self.face_cascade = None
    
    def _detect_face_center(self, video_file: Path, start_time: float, duration: float) -> Optional[float]:
        """
        비디오에서 얼굴의 평균 X 좌표를 찾습니다.
        
        Args:
            video_file: 비디오 파일 경로
            start_time: 시작 시간 (초)
            duration: 길이 (초)
            
        Returns:
            얼굴 중심 X 좌표 (0-1 범위, None이면 얼굴 미감지)
        """
        if not FACE_DETECTION_AVAILABLE or self.face_cascade is None:
            return None
        
        try:
            # 비디오 열기
            cap = cv2.VideoCapture(str(video_file))
            if not cap.isOpened():
                logger.warning("비디오 열기 실패")
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 샘플링할 프레임 수 (최대 10개)
            total_frames = int(duration * fps)
            sample_count = min(10, total_frames)
            frame_interval = max(1, total_frames // sample_count)
            
            # 시작 프레임으로 이동
            start_frame = int(start_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            face_centers = []
            
            for i in range(sample_count):
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 그레이스케일 변환
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 얼굴 감지
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                if len(faces) > 0:
                    # 가장 큰 얼굴 선택 (면적 기준)
                    largest_face = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = largest_face
                    
                    # 얼굴 중심 X 좌표 (0-1 범위로 정규화)
                    face_center_x = (x + w // 2) / width
                    face_centers.append(face_center_x)
                    logger.debug(f"프레임 {i}: 얼굴 감지, 중심 X = {face_center_x:.3f}")
                
                # 다음 샘플 프레임으로 이동
                for _ in range(frame_interval - 1):
                    cap.read()
            
            cap.release()
            
            if len(face_centers) == 0:
                logger.info("얼굴을 감지하지 못했습니다. 중앙 크롭 사용.")
                return None
            
            # 평균 얼굴 중심 계산
            avg_face_center = sum(face_centers) / len(face_centers)
            logger.info(f"얼굴 감지 완료: 평균 중심 X = {avg_face_center:.3f} ({len(face_centers)}/{sample_count} 프레임)")
            return avg_face_center
            
        except Exception as e:
            logger.warning(f"얼굴 감지 오류: {e}. 중앙 크롭 사용.")
            return None
    
    def _calculate_crop_position(
        self,
        width: int,
        height: int,
        target_width: int,
        target_height: int,
        face_center_x: Optional[float] = None
    ) -> Tuple[int, int, int, int]:
        """
        크롭 위치를 계산합니다.
        
        Args:
            width: 원본 너비
            height: 원본 높이
            target_width: 목표 너비
            target_height: 목표 높이
            face_center_x: 얼굴 중심 X 좌표 (0-1, None이면 중앙)
            
        Returns:
            (new_width, new_height, x_offset, y_offset)
        """
        if width / height > target_width / target_height:
            # 가로가 더 긴 경우: 높이 기준
            new_height = height
            new_width = int(height * target_width / target_height)
            
            # 얼굴 중심 기반 X 오프셋 계산
            if face_center_x is not None:
                # 얼굴 중심을 기준으로 크롭 위치 계산
                crop_center_x = face_center_x * width
                x_offset = int(crop_center_x - new_width // 2)
                # 경계 체크
                x_offset = max(0, min(x_offset, width - new_width))
                logger.info(f"얼굴 기반 크롭: face_center={face_center_x:.3f}, x_offset={x_offset}")
            else:
                # 중앙 크롭 (fallback)
                x_offset = (width - new_width) // 2
            
            y_offset = 0
        else:
            # 세로가 더 긴 경우: 너비 기준
            new_width = width
            new_height = int(width * target_height / target_width)
            x_offset = 0
            y_offset = (height - new_height) // 2
        
        return new_width, new_height, x_offset, y_offset
    
    def generate_clip(
        self,
        video_file: Path,
        clip_segment: Dict,
        transcript: List[Dict],
        output_dir: Path,
        output_filename: str
    ) -> Dict:
        """
        클립을 생성하고 자막을 추가합니다.
        
        Args:
            video_file: 원본 비디오 파일
            clip_segment: 클립 구간 정보 (start, end, hook)
            transcript: 전체 전사본
            output_dir: 출력 디렉토리
            output_filename: 출력 파일명
            
        Returns:
            {
                "filename": "videoId_clip_01.mp4",
                "start": 120.5,
                "end": 155.0,
                "duration": 34.5,
                "hook": "...",
                "confidence": 0.92
            }
        """
        logger.info(f"클립 생성: {clip_segment['start']:.1f}s - {clip_segment['end']:.1f}s")
        
        output_file = output_dir / output_filename
        output_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = clip_segment["start"]
        end_time = clip_segment["end"]
        duration = end_time - start_time
        
        # 해당 구간의 텍스트 추출
        clip_text_segments = [
            seg for seg in transcript
            if start_time <= seg["start"] < end_time
        ]
        
        # SRT 자막 파일 생성
        srt_file = output_dir / f"{output_filename}.srt"
        self._create_srt_file(srt_file, clip_text_segments, start_time)
        
        # FFmpeg로 클립 생성 (9:16, 자막 포함)
        self._create_clip_with_subtitles(
            video_file,
            output_file,
            start_time,
            duration,
            srt_file
        )
        
        return {
            "filename": output_filename,
            "start": start_time,
            "end": end_time,
            "duration": round(duration, 2),
            "hook": clip_segment.get("hook", ""),
            "confidence": clip_segment.get("confidence", 0.8)
        }
    
    def _create_srt_file(
        self,
        srt_file: Path,
        text_segments: List[Dict],
        offset: float
    ):
        """SRT 자막 파일 생성 (Short 스타일)"""
        srt_content = []
        
        for i, seg in enumerate(text_segments, 1):
            # 시간 조정 (오프셋 제거)
            start = seg["start"] - offset
            end = seg["end"] - offset
            
            # SRT 시간 형식
            start_str = self._format_srt_time(start)
            end_str = self._format_srt_time(end)
            
            # 텍스트를 짧은 줄로 분할 (4:5 비율 영상에 맞게)
            # 세로 영상은 가로가 좁으므로 줄 길이를 더 짧게
            words = seg["text"].split()
            lines = []
            current_line = []
            
            for word in words:
                current_line.append(word)
                # 세로 영상에 맞게 줄 길이 제한 (약 25-30자)
                if len(current_line) >= 4 or len(" ".join(current_line)) > 30:
                    lines.append(" ".join(current_line))
                    current_line = []
            
            if current_line:
                lines.append(" ".join(current_line))
            
            # SRT 항목 추가
            srt_content.append(f"{i}")
            srt_content.append(f"{start_str} --> {end_str}")
            srt_content.append("\n".join(lines))
            srt_content.append("")
        
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_content))
    
    def _format_srt_time(self, seconds: float) -> str:
        """초를 SRT 시간 형식으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _create_clip_with_subtitles(
        self,
        input_file: Path,
        output_file: Path,
        start_time: float,
        duration: float,
        srt_file: Path
    ):
        """FFmpeg로 클립 생성 (4:5, 자막 포함)"""
        try:
            # 비디오 정보 가져오기
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=p=0',
                str(input_file)
            ]
            
            result = subprocess.run(
                probe_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            width, height = map(int, result.stdout.strip().split(','))
            
            # 4:5 비율 계산 (1080×1350)
            target_width = 1080
            target_height = 1350
            
            # 얼굴 감지 기반 스마트 크롭
            logger.info("얼굴 감지 시작...")
            face_center_x = self._detect_face_center(input_file, start_time, duration)
            
            # 크롭 위치 계산 (얼굴 중심 또는 중앙)
            new_width, new_height, x_offset, y_offset = self._calculate_crop_position(
                width, height, target_width, target_height, face_center_x
            )
            
            logger.info(f"크롭 설정: {new_width}x{new_height} @ ({x_offset}, {y_offset})")
            
            # FFmpeg 필터
            # 1. 클립 자르기
            # 2. 크롭 (4:5)
            # 3. 리사이즈
            # 4. 자막 추가 (filter_complex에 포함)
            # 5. 오디오 정규화
            
            # 1단계: 비디오 크롭 및 리사이즈 (자막 없이)
            # 오디오는 별도로 처리하지 않고 -ss와 -t로 자동 처리
            temp_output = output_file.parent / f"{output_file.stem}_temp.mp4"
            
            # 1단계: 자막 없이 클립 생성 (고화질 설정)
            cmd1 = [
                'ffmpeg',
                '-i', str(input_file),
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f"crop={new_width}:{new_height}:{x_offset}:{y_offset},scale={target_width}:{target_height}",
                '-c:v', 'libx264',
                '-preset', 'medium',  # fast → medium (더 나은 압축)
                '-crf', '18',  # 23 → 18 (더 높은 화질, 낮을수록 좋음)
                '-profile:v', 'high',  # 고품질 프로파일
                '-pix_fmt', 'yuv420p',  # 호환성 보장
                '-c:a', 'aac',
                '-b:a', '192k',  # 128k → 192k (더 나은 오디오 품질)
                '-movflags', '+faststart',
                '-y',
                str(temp_output)
            ]
            
            logger.info(f"FFmpeg 1단계 실행 (자막 없이): {' '.join(cmd1)}")
            result = subprocess.run(cmd1, capture_output=True, text=True, check=True)
            
            # 2단계: 자막 추가
            if srt_file.exists():
                # 자막 파일 경로를 절대 경로로 변환하고 특수문자 이스케이프
                srt_path_abs = str(srt_file.absolute())
                # Windows 경로 구분자 처리
                srt_path_abs = srt_path_abs.replace("\\", "/")
                
                # FFmpeg subtitles 필터 사용 (libass 기반, 더 안정적)
                # 4:5 비율 영상에 맞춘 자막 스타일
                # FontSize: 60 → 40 (더 작게)
                # MarginV: 150 → 80 (하단에 더 가깝게)
                # Alignment: 2 (하단 중앙)
                cmd2 = [
                    'ffmpeg',
                    '-i', str(temp_output),
                    '-vf', f"subtitles={srt_path_abs}:force_style='FontName=Arial Black,FontSize=40,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Shadow=1,MarginV=80,Alignment=2'",
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '18',
                    '-profile:v', 'high',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'copy',  # 오디오는 재인코딩 없이 복사
                    '-movflags', '+faststart',
                    '-y',
                    str(output_file)
                ]
                
                logger.info(f"FFmpeg 2단계 실행 (자막 추가): {' '.join(cmd2)}")
                try:
                    result = subprocess.run(cmd2, capture_output=True, text=True, check=True)
                    logger.info("자막 추가 완료")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"자막 추가 실패: {e.stderr[:200] if e.stderr else 'Unknown error'}")
                    logger.warning("자막 없이 저장합니다")
                    import shutil
                    shutil.copy2(temp_output, output_file)
            else:
                # 자막 파일이 없으면 임시 파일을 그대로 사용
                logger.warning("자막 파일이 없습니다. 자막 없이 저장합니다")
                import shutil
                shutil.copy2(temp_output, output_file)
            
            # 임시 파일 삭제
            if temp_output.exists():
                temp_output.unlink()
            
            cmd = cmd1  # 로깅용
            
            logger.info(f"FFmpeg 실행: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"클립 생성 완료: {output_file}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 오류: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"클립 생성 오류: {e}")
            raise

