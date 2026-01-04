"""
쇼츠 영상 자동 병합 모듈
FFmpeg를 사용하여 여러 개의 짧은 영상을 하나로 이어붙입니다.
재인코딩 없이 빠르게 처리합니다.
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoMerger:
    """영상 병합 클래스"""
    
    def __init__(self, keyword: str = None, video_order: list = None, video_texts: dict = None, aspect_ratio: str = '4:5'):
        # 상위 디렉토리 기준으로 경로 설정
        BASE_DIR = Path(__file__).parent.parent
        self.raw_dir = BASE_DIR / "videos" / "raw"
        self.final_dir = BASE_DIR / "videos" / "final"
        self.video_order = video_order  # 사용자가 지정한 순서
        self.video_texts = video_texts or {}  # 각 영상의 하단 텍스트 {filename: text}
        self.aspect_ratio = aspect_ratio  # 출력 비율 (예: '9:16', '16:9', '1:1')
        
        # 키워드 기반 파일명 생성
        if keyword:
            # 키워드를 파일명으로 사용 (특수문자 제거)
            safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_keyword = safe_keyword.replace(' ', '_')
            if not safe_keyword:
                safe_keyword = "merged"
            # 중복 방지를 위해 타임스탬프 추가
            import time
            timestamp = int(time.time())
            filename = f"{safe_keyword}_{timestamp}.mp4"
        else:
            # 키워드가 없으면 타임스탬프만 사용
            import time
            timestamp = int(time.time())
            filename = f"merged_{timestamp}.mp4"
        
        self.output_file = self.final_dir / filename
        
        # 디렉토리 생성
        self.final_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_files(self) -> list:
        """raw 디렉토리에서 mp4 파일 목록을 가져옵니다 (사용자 지정 순서 또는 업로드 순서대로 정렬)."""
        if not self.raw_dir.exists():
            logger.error(f"{self.raw_dir} 디렉토리가 없습니다.")
            return []
        
        video_files = list(self.raw_dir.glob("*.mp4"))
        
        if not video_files:
            logger.warning(f"{self.raw_dir}에 mp4 파일이 없습니다.")
            return []
        
        # 사용자가 지정한 순서가 있으면 그 순서대로 정렬
        if self.video_order and isinstance(self.video_order, list) and len(self.video_order) > 0:
            try:
                # 파일명을 키로 하는 딕셔너리 생성
                file_dict = {f.name: f for f in video_files}
                ordered_files = []
                
                # 지정된 순서대로 파일 추가
                for filename in self.video_order:
                    if filename in file_dict:
                        ordered_files.append(file_dict[filename])
                    else:
                        logger.warning(f"순서에 지정된 파일을 찾을 수 없습니다: {filename}")
                
                # 순서에 없는 파일들은 타임스탬프 순으로 추가
                remaining_files = [f for f in video_files if f.name not in self.video_order]
                if remaining_files:
                    def get_timestamp(filename):
                        try:
                            parts = filename.stem.split('_')
                            if parts[0].isdigit():
                                return int(parts[0])
                            return 0
                        except:
                            return 0
                    remaining_files = sorted(remaining_files, key=get_timestamp, reverse=True)
                    ordered_files.extend(remaining_files)
                
                # 정렬된 파일이 있으면 사용, 없으면 원래 순서 사용
                if ordered_files:
                    video_files = ordered_files
                    logger.info(f"{len(video_files)}개의 영상을 사용자 지정 순서로 정렬했습니다:")
                else:
                    logger.warning("사용자 지정 순서로 정렬된 파일이 없어 기본 순서를 사용합니다.")
            except Exception as e:
                logger.error(f"사용자 지정 순서 정렬 중 오류 발생: {e}")
                logger.info("기본 순서로 정렬합니다.")
        else:
            # 타임스탬프로 정렬 (업로드 순서)
            # 파일명 형식: {timestamp}_{original_filename} 또는 {original_filename}
            def get_timestamp(filename):
                try:
                    # 파일명 앞부분의 타임스탬프 추출
                    parts = filename.stem.split('_')
                    if parts[0].isdigit() and len(parts[0]) >= 10:  # 타임스탬프는 보통 10자리 이상
                        return int(parts[0])
                    # 타임스탬프가 없으면 파일 수정 시간 사용
                    return int(filename.stat().st_mtime)
                except:
                    # 오류 발생 시 파일 수정 시간 사용
                    try:
                        return int(filename.stat().st_mtime)
                    except:
                        return 0
            
            video_files = sorted(video_files, key=get_timestamp, reverse=True)  # 역순 정렬
            logger.info(f"{len(video_files)}개의 영상을 찾았습니다 (역순):")
        
        for i, video in enumerate(video_files, 1):
            display_name = video.name.split('_', 1)[1] if '_' in video.name else video.name
            logger.info(f"  {i}. {display_name}")
        
        return video_files
    
    def create_concat_file(self, video_files: list) -> str:
        """FFmpeg concat용 파일 리스트를 생성합니다."""
        concat_content = []
        
        for video_file in video_files:
            # 절대 경로로 변환 (FFmpeg는 상대 경로에 문제가 있을 수 있음)
            abs_path = video_file.resolve()
            abs_path_str = str(abs_path)
            
            # Windows 경로 처리: 백슬래시를 슬래시로 변환
            # FFmpeg는 Unix 스타일 경로를 선호
            abs_path_str = abs_path_str.replace('\\', '/')
            
            concat_content.append(f"file '{abs_path_str}'")
        
        # 임시 파일 생성
        with NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('\n'.join(concat_content))
            concat_file_path = f.name
        
        logger.debug(f"Concat 파일 생성: {concat_file_path}")
        logger.debug(f"Concat 내용:\n{chr(10).join(concat_content)}")
        
        return concat_file_path
    
    def check_ffmpeg(self) -> bool:
        """FFmpeg가 설치되어 있는지 확인합니다."""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg가 설치되어 있지 않거나 PATH에 없습니다.")
            logger.error("설치 방법: https://ffmpeg.org/download.html")
            return False
    
    def merge_videos(self, video_files: list) -> bool:
        """FFmpeg를 사용하여 영상들을 병합합니다."""
        if not video_files:
            logger.error("병합할 영상이 없습니다.")
            return False
        
        # 영상이 1개여도 재인코딩 + 비율 보정 로직을 거쳐야 함
        # (단순 복사 시 aspect_ratio, scale, pad 적용이 안 됨)
        # 따라서 이 분기를 제거하고 아래 재인코딩 로직을 공통으로 사용
        
        # concat 파일 생성
        concat_file = self.create_concat_file(video_files)
        
        try:
            logger.info("영상 병합 시작...")
            
            # 첫 번째 영상의 정보를 가져와서 출력 형식 결정
            first_video = video_files[0]
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
                '-of', 'json',
                str(first_video)
            ]
            
            # 출력 비율에 따른 목표 해상도 계산
            aspect_parts = self.aspect_ratio.split(':')
            aspect_w = float(aspect_parts[0])
            aspect_h = float(aspect_parts[1])
            aspect_ratio_value = aspect_w / aspect_h
            
            # 기준 해상도 (가로 기준)
            base_width = 1080
            target_width = int(base_width)
            target_height = int(base_width / aspect_ratio_value)
            
            logger.info(f"출력 비율: {self.aspect_ratio} ({target_width}x{target_height})")
            
            # 첫 번째 영상의 원본 해상도 확인 (비율 계산용)
            original_width, original_height = 1080, 1920
            try:
                probe_result = subprocess.run(
                    probe_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                import json as json_lib
                if probe_result.returncode == 0:
                    video_info = json_lib.loads(probe_result.stdout)
                    streams = video_info.get('streams', [])
                    if streams:
                        original_width = streams[0].get('width', 1080)
                        original_height = streams[0].get('height', 1920)
                        logger.info(f"기준 영상 정보: {original_width}x{original_height}")
            except Exception as e:
                logger.warning(f"영상 정보 확인 실패, 기본값 사용: {e}")
            
            width, height = target_width, target_height
            
            # filter_complex를 사용하여 안정적인 병합
            # 각 영상을 개별적으로 처리하고 concat 필터로 병합
            import tempfile
            
            # 임시 재인코딩된 파일들을 저장할 리스트
            temp_files = []
            
            try:
                # 각 영상을 동일한 형식으로 재인코딩
                logger.info("각 영상을 동일 형식으로 재인코딩 중...")
                for i, video_file in enumerate(video_files):
                    # 임시 파일을 videos 디렉토리에 생성 (절대 경로 사용)
                    temp_dir = self.raw_dir.parent
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix='.mp4',
                        delete=False,
                        dir=str(temp_dir)
                    )
                    temp_file.close()
                    temp_file_path = Path(temp_file.name)
                    # 파일이 실제로 생성되었는지 확인
                    if not temp_file_path.exists():
                        logger.error(f"임시 파일 생성 실패: {temp_file_path}")
                        raise Exception(f"임시 파일 생성 실패: {temp_file_path}")
                    temp_files.append(temp_file_path)
                    logger.debug(f"임시 파일 생성: {temp_file_path}")
                    
                    # 각 영상에 텍스트 오버레이 추가 (있는 경우)
                    video_filename = video_file.name
                    text_overlay = self.video_texts.get(video_filename, '')
                    
                    # 비디오 필터 구성 (letterbox 방식)
                    # 영상 비율을 유지하면서 목표 비율에 맞춤
                    # 세로가 짧으면 상하단에 검은색 여백 추가
                    # 목표 해상도로 강제 변환 (4:5 = 1080x1350, 9:16 = 1080x1920 등)
                    # scale로 비율 유지하며 스케일링 후, pad로 정확히 목표 해상도로 맞춤
                    # pad는 자동으로 목표 해상도로 맞춰주므로 추가 scale 불필요
                    video_filters = [
                        f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2',  # 비율 유지하며 크기 조정 (짝수로)
                        f'pad={width}:{height}:({width}-iw)/2:({height}-ih)/2:color=black',  # 검은색 여백 추가 (중앙 정렬, 정확한 계산)
                        f'scale={width}:{height}'  # 최종 해상도 강제 설정 (보장)
                    ]
                    
                    # 텍스트가 있으면 오버레이 추가
                    if text_overlay:
                        # 텍스트를 줄바꿈으로 분리
                        lines = text_overlay.split('\n')
                        
                        # 각 줄을 별도의 drawtext로 그리기 (여러 줄 지원)
                        # 해상도에 비례하여 폰트 크기 계산 (1080 기준으로 60px)
                        # 높은 해상도에서는 더 큰 폰트 사용
                        base_font_size = 60
                        font_size = int(base_font_size * (height / 1920)) if height > 0 else base_font_size
                        font_size = max(font_size, 48)  # 최소 48px
                        
                        # 줄 간격을 폰트 크기에 비례하여 계산 (폰트 크기의 1.5배)
                        line_height = int(font_size * 1.5)
                        base_y_offset = 250  # 상단 여백 (더 아래로)
                        
                        for i, line in enumerate(lines):
                            if line.strip():  # 빈 줄은 제외
                                # 각 줄을 안전하게 이스케이프
                                escaped_line = line.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                                # 상단에서 아래로 내려가며 각 줄 배치
                                y_offset = base_y_offset + i * line_height
                                # 글자 아웃라인 두께를 폰트 크기에 비례하여 계산 (더 두껍게)
                                border_width = max(4, int(font_size / 12))
                                # 4초 동안만 표시 (enable='between(t,0,4)')
                                # 흰 글씨 + 검은 아웃라인 (배경 없음)
                                text_filter = f"drawtext=text='{escaped_line}':fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y={y_offset}:borderw={border_width}:bordercolor=black@1.0:enable='between(t,0,4)'"
                                video_filters.append(text_filter)
                    
                    vf_param = ','.join(video_filters)
                    
                    # 각 영상을 동일한 형식으로 재인코딩 (최고 화질 설정)
                    # 목표 해상도로 강제 변환 (4:5 = 1080x1350 등)
                    # pad 필터가 이미 목표 해상도로 맞춰주므로 -s 옵션 불필요 (충돌 방지)
                    encode_cmd = [
                        'ffmpeg',
                        '-i', str(video_file),
                        '-vf', vf_param,
                        '-c:v', 'libx264',
                        '-preset', 'veryslow',  # 최고 화질 (처리 시간은 오래 걸림)
                        '-crf', '10',  # 10은 거의 무손실 수준의 고화질 (낮을수록 고화질, 0-51 범위, 10은 매우 고화질)
                        '-profile:v', 'high',  # High profile 사용
                        '-level', '4.2',  # H.264 레벨 (더 높은 레벨)
                        '-r', '30',
                        '-pix_fmt', 'yuv420p',
                        '-tune', 'film',  # 필름 콘텐츠 최적화
                        '-x264-params', 'keyint=60:min-keyint=60:scenecut=0:aq-mode=3:aq-strength=1.0:merange=24:subme=10:trellis=2',  # 최고품질 인코딩 파라미터
                        '-c:a', 'aac',
                        '-b:a', '320k',  # 오디오 비트레이트 최대화
                        '-y',
                        str(temp_files[-1])
                    ]
                    
                    encode_result = subprocess.run(
                        encode_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if encode_result.returncode != 0:
                        logger.error(f"영상 {i+1} 재인코딩 실패: {encode_result.stderr}")
                        raise Exception(f"영상 {i+1} 재인코딩 실패")
                    
                    # 재인코딩된 파일이 실제로 존재하는지 확인
                    if not temp_files[-1].exists():
                        logger.error(f"재인코딩된 파일이 존재하지 않습니다: {temp_files[-1]}")
                        raise Exception(f"재인코딩된 파일이 존재하지 않습니다: {temp_files[-1]}")
                    
                    file_size = temp_files[-1].stat().st_size / (1024 * 1024)  # MB
                    logger.info(f"영상 {i+1}/{len(video_files)} 재인코딩 완료 (크기: {file_size:.2f} MB)")
                
                # 재인코딩된 파일들로 concat 파일 생성
                # 모든 임시 파일이 존재하는지 먼저 확인
                for temp_file in temp_files:
                    if not temp_file.exists():
                        logger.error(f"임시 파일이 존재하지 않습니다: {temp_file}")
                        raise Exception(f"임시 파일이 존재하지 않습니다: {temp_file}")
                    file_size = temp_file.stat().st_size
                    if file_size == 0:
                        logger.error(f"임시 파일이 비어있습니다: {temp_file}")
                        raise Exception(f"임시 파일이 비어있습니다: {temp_file}")
                    logger.debug(f"임시 파일 확인: {temp_file} (크기: {file_size / (1024*1024):.2f} MB)")
                
                concat_file_normalized = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.txt',
                    delete=False,
                    encoding='utf-8'
                )
                
                for temp_file in temp_files:
                    abs_path = temp_file.resolve()
                    abs_path_str = str(abs_path).replace('\\', '/')
                    concat_file_normalized.write(f"file '{abs_path_str}'\n")
                    logger.debug(f"Concat 파일에 추가: {abs_path_str}")
                
                concat_file_normalized.close()
                concat_file_path = concat_file_normalized.name
                logger.info(f"Concat 파일 생성: {concat_file_path}")
                
                # 재인코딩된 파일들을 concat (스트림 복사)
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file_path,
                    '-c', 'copy',  # 재인코딩된 파일들이므로 copy 가능
                    '-movflags', '+faststart',
                    '-y',
                    str(self.output_file)
                ]
                
                logger.info(f"FFmpeg 병합 명령 실행: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0:
                    file_size = self.output_file.stat().st_size / (1024 * 1024)  # MB
                    logger.info(f"✅ 영상 병합 완료: {self.output_file}")
                    logger.info(f"   파일 크기: {file_size:.2f} MB")
                    return True
                else:
                    logger.error(f"❌ FFmpeg 병합 실패:")
                    logger.error(result.stderr)
                    return False
                    
            finally:
                # 임시 파일들 정리
                try:
                    if 'concat_file_path' in locals():
                        os.unlink(concat_file_path)
                except:
                    pass
                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            os.unlink(temp_file)
                    except:
                        pass
                
        except Exception as e:
            logger.error(f"영상 병합 중 오류 발생: {e}")
            return False
        finally:
            # 임시 concat 파일 삭제
            try:
                os.unlink(concat_file)
            except:
                pass
    
    def run(self):
        """전체 병합 프로세스를 실행합니다."""
        logger.info("=" * 50)
        logger.info("쇼츠 영상 병합 시작")
        logger.info("=" * 50)
        
        # FFmpeg 확인
        if not self.check_ffmpeg():
            return
        
        # 영상 파일 목록 가져오기
        video_files = self.get_video_files()
        
        if not video_files:
            return
        
        # 영상 병합
        success = self.merge_videos(video_files)
        
        if success:
            logger.info("=" * 50)
            logger.info("병합 프로세스 완료")
            logger.info("=" * 50)
        else:
            logger.error("병합 프로세스 실패")


if __name__ == "__main__":
    merger = VideoMerger()
    merger.run()
