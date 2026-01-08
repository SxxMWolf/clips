"""
쇼츠 영상 자동 병합 웹 인터페이스
Flask를 사용한 웹 대시보드
"""

import os
import json
import threading
import shutil
import logging
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from dotenv import load_dotenv
from merge.merge import VideoMerger
from prompt.prompt_generator import PromptGenerator
import requests

# 로거 설정
logger = logging.getLogger(__name__)

# Flask 개발 서버 경고 메시지 숨기기
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="werkzeug")
warnings.filterwarnings("ignore", message=".*development server.*")
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/merge')
def merge_page():
    """영상 병합 페이지"""
    return render_template('merge.html')


@app.route('/ai-clip')
def ai_clip_page():
    """AI 클립 생성 페이지"""
    return render_template('ai_clip.html')


@app.route('/ai-prompt')
def ai_prompt_page():
    """AI 프롬프트 생성 페이지"""
    return render_template('ai_prompt.html')


@app.route('/favicon.ico')
def favicon():
    """Favicon 요청 처리 (404 방지)"""
    return Response(status=204)  # No Content - 브라우저가 404를 표시하지 않음


@app.route('/api/status')
def get_status():
    """현재 상태 정보 반환"""
    raw_dir = Path("videos/raw")
    final_dir = Path("videos/final")
    
    # 원본 영상 목록 (역순 정렬 - 최신이 먼저)
    raw_videos = []
    if raw_dir.exists():
        video_files = list(raw_dir.glob("*.mp4"))
        # 타임스탬프로 역순 정렬 (최신이 먼저)
        raw_videos = sorted(
            [f.name for f in video_files],
            key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else 0,
            reverse=True
        )
    
    # 최신 병합 영상 찾기 (가장 최근 수정된 파일)
    final_videos = []
    if final_dir.exists():
        final_videos = list(final_dir.glob("*.mp4"))
        if final_videos:
            # 수정 시간 기준으로 정렬 (최신순)
            final_videos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    merged_exists = len(final_videos) > 0
    merged_size = 0
    latest_merged = None
    if merged_exists:
        latest_merged = final_videos[0]
        merged_size = latest_merged.stat().st_size / (1024 * 1024)  # MB
    
    return jsonify({
        'raw_videos': raw_videos,
        'raw_count': len(raw_videos),
        'merged_exists': merged_exists,
        'merged_size': round(merged_size, 2),
        'latest_merged': latest_merged.name if latest_merged else None
    })


@app.route('/api/merge', methods=['POST'])
def merge_videos():
    """영상 병합 실행"""
    try:
        data = request.json or {}
        keyword = (data.get('keyword') or '').strip() if data.get('keyword') else ''
        video_order = data.get('video_order')  # 사용자가 지정한 순서
        video_texts = data.get('video_texts')  # 각 영상의 하단 텍스트
        aspect_ratio = data.get('aspect_ratio', '4:5')  # 출력 비율 (기본값: 4:5)
        add_letterbox = data.get('add_letterbox', True)  # letterbox 추가 여부 (기본값: True)
        
        # video_order가 빈 리스트이거나 None이면 None으로 설정
        if video_order and len(video_order) == 0:
            video_order = None
        
        try:
            merger = VideoMerger(keyword=keyword if keyword else None, video_order=video_order, video_texts=video_texts, aspect_ratio=aspect_ratio, add_letterbox=add_letterbox)
        except Exception as e:
            logger.error(f"VideoMerger 초기화 오류: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'VideoMerger 초기화 실패: {str(e)}'
            }), 500
        
        # output_file 확인
        if not hasattr(merger, 'output_file') or not merger.output_file:
            logger.error("merger.output_file이 설정되지 않았습니다.")
            return jsonify({
                'success': False,
                'message': '출력 파일 설정 오류'
            }), 500
        
        output_filename = str(merger.output_file.name) if hasattr(merger.output_file, 'name') else str(merger.output_file)
        
        # 별도 스레드에서 실행 (비동기)
        def run_merge():
            try:
                logger.info(f"병합 시작: keyword={keyword}, video_order={video_order}")
                merger.run()
                logger.info(f"병합 완료: {merger.output_file}")
            except Exception as e:
                logger.error(f"병합 실행 중 오류: {e}")
                logger.error(f"상세 오류: {traceback.format_exc()}")
        
        thread = threading.Thread(target=run_merge)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '영상 병합이 시작되었습니다.',
            'filename': output_filename
        })
    except Exception as e:
        logger.error(f"병합 요청 처리 오류: {e}")
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'오류 발생: {str(e)}'
        }), 500


@app.route('/api/upload/video', methods=['POST'])
def upload_video():
    """영상 파일 업로드 (병합용)"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '파일이 없습니다.'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '파일이 선택되지 않았습니다.'
            }), 400
        
        if not file.filename.lower().endswith('.mp4'):
            return jsonify({
                'success': False,
                'message': 'MP4 파일만 업로드 가능합니다.'
            }), 400
        
        # 업로드 순서를 타임스탬프로 저장
        import time
        timestamp = int(time.time() * 1000)  # 밀리초 단위
        from werkzeug.utils import secure_filename
        filename = f"{timestamp:015d}_{secure_filename(file.filename)}"
        
        raw_dir = Path("videos/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = raw_dir / filename
        file.save(str(file_path))
        
        return jsonify({
            'success': True,
            'message': '파일이 업로드되었습니다.',
            'filename': filename
        })
    except Exception as e:
        logger.error(f"파일 업로드 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'업로드 실패: {str(e)}'
        }), 500


@app.route('/api/upload/video/clear', methods=['POST'])
def clear_videos():
    """모든 업로드된 영상 파일을 삭제"""
    try:
        raw_dir = Path("videos/raw")
        
        deleted_count = 0
        if raw_dir.exists():
            for file in raw_dir.glob("*.mp4"):
                try:
                    file.unlink()  # 파일 삭제
                    deleted_count += 1
                except Exception as e:
                    # 개별 파일 삭제 실패 시 로그만 남기고 계속 진행
                    logger.error(f"파일 삭제 실패 {file.name}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count}개의 파일이 삭제되었습니다.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'파일 이동 실패: {str(e)}'
        }), 500


@app.route('/videos/<path:filename>')
def serve_video(filename):
    """영상 파일 제공 (final 폴더)"""
    return send_from_directory('videos/final', filename)


# AI 클리핑 API 엔드포인트 (FastAPI 프록시)
AI_API_BASE = "http://localhost:8000"

def handle_ai_api_error(e):
    """AI API 에러 처리 헬퍼"""
    return jsonify({
        'success': False,
        'message': f'오류 발생: {str(e)}'
    }), 500

def proxy_ai_request(method, endpoint, **kwargs):
    """FastAPI 서버로 요청 프록시"""
    try:
        url = f"{AI_API_BASE}{endpoint}"
        if method == 'GET':
            response = requests.get(url, timeout=30, **kwargs)
        elif method == 'POST':
            response = requests.post(url, timeout=30, **kwargs)
        else:
            raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
        return jsonify(response.json())
    except Exception as e:
        return handle_ai_api_error(e)

@app.route('/api/ai/import-youtube', methods=['POST'])
def ai_import_youtube():
    """YouTube 영상 다운로드 (AI 클리핑용)"""
    data = request.json
    url = data.get('url')
    prompt = data.get('prompt', 'Find the most engaging and viral moments')
    
    if not url:
        return jsonify({
            'success': False,
            'message': 'YouTube URL이 필요합니다.'
        }), 400
    
    return proxy_ai_request('POST', '/api/video/import/youtube', json={"url": url, "prompt": prompt})


@app.route('/api/ai/video-status/<video_id>')
def ai_video_status(video_id):
    """비디오 처리 상태 확인"""
    return proxy_ai_request('GET', f'/api/video/status/{video_id}')


@app.route('/api/ai/generate-clips', methods=['POST'])
def ai_generate_clips():
    """AI 클립 생성"""
    data = request.json
    video_id = data.get('video_id')
    prompt = data.get('prompt', 'Find the most engaging and viral moments')
    
    if not video_id:
        return jsonify({
            'success': False,
            'message': 'video_id가 필요합니다.'
        }), 400
    
    return proxy_ai_request('POST', '/api/video/generate-clips', json={"video_id": video_id, "prompt": prompt})


@app.route('/api/ai/clips/<video_id>')
def ai_get_clips(video_id):
    """생성된 클립 목록 조회"""
    return proxy_ai_request('GET', f'/api/clips/{video_id}')


@app.route('/api/ai/clip/file/<video_id>/<filename>')
def ai_serve_clip(video_id, filename):
    """AI 생성 클립 파일 제공"""
    clip_file = Path(f"videos/clips/{video_id}/{filename}")
    if clip_file.exists():
        return send_from_directory(f'videos/clips/{video_id}', filename)
    else:
        return jsonify({'error': 'File not found'}), 404


@app.route('/api/ai/generate-prompt', methods=['POST'])
def generate_ai_prompt():
    """AI 프롬프트 생성"""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        prompt_type = data.get('prompt_type', 'video')  # 'video' 또는 'cat_travel'
        
        if not topic:
            return jsonify({
                'success': False,
                'message': '주제를 입력해주세요.'
            }), 400
        
        prompt_generator = PromptGenerator()
        result = prompt_generator.generate_prompt(topic, prompt_type=prompt_type)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류 발생: {str(e)}'
        }), 500


if __name__ == '__main__':
    # 디렉토리 생성
    Path("videos/raw").mkdir(parents=True, exist_ok=True)
    Path("videos/final").mkdir(parents=True, exist_ok=True)
    Path("videos/downloads").mkdir(parents=True, exist_ok=True)
    Path("videos/clips").mkdir(parents=True, exist_ok=True)
    Path("transcripts").mkdir(parents=True, exist_ok=True)
    Path("templates").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True)
    
    print("=" * 50)
    print("쇼츠 영상 자동 병합 웹 서버")
    print("=" * 50)
    print("브라우저에서 http://localhost:5001 접속")
    print("=" * 50)
    
    # Flask 개발 서버 경고 메시지 숨기기
    import sys
    import warnings
    if not sys.warnoptions:
        warnings.simplefilter("ignore")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        raise

