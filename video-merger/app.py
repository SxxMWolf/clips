"""
Short Video Auto-Merge Web Interface
Web Dashboard using Flask
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
import re

# Logger setup
logger = logging.getLogger(__name__)

# Suppress Flask dev server warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="werkzeug")
warnings.filterwarnings("ignore", message=".*development server.*")
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


@app.route('/')
def index():
    """Main Page"""
    return render_template('index.html')


@app.route('/merge')
def merge_page():
    """Video Merge Page"""
    return render_template('merge.html')


@app.route('/ai-prompt')
def ai_prompt_page():
    """AI Prompt Generation Page"""
    return render_template('ai_prompt.html')


@app.route('/favicon.ico')
def favicon():
    """Handle Favicon request (avoid 404)"""
    return Response(status=204)  # No Content


@app.route('/api/status')
def get_status():
    """Return current status information"""
    raw_dir = Path("videos/raw")
    final_dir = Path("videos/final")
    
    # Raw video list (reverse sort - newest first)
    raw_videos = []
    if raw_dir.exists():
        video_files = list(raw_dir.glob("*.mp4"))
        # Sort by timestamp (newest first)
        raw_videos = sorted(
            [f.name for f in video_files],
            key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else 0,
            reverse=True
        )
    
    # Find latest merged video
    final_videos = []
    if final_dir.exists():
        final_videos = list(final_dir.glob("*.mp4"))
        if final_videos:
            # Sort by modification time (newest first)
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
    """Execute video merge"""
    try:
        data = request.json or {}
        keyword = (data.get('keyword') or '').strip() if data.get('keyword') else ''
        video_order = data.get('video_order')  # User specified order
        video_texts = data.get('video_texts')  # Footer text for each video
        aspect_ratio = data.get('aspect_ratio', '4:5')  # Output ratio (default: 4:5)
        add_letterbox = data.get('add_letterbox', True)  # Letterbox option (default: True)
        
        # Set to None if video_order is empty
        if video_order and len(video_order) == 0:
            video_order = None
        
        try:
            merger = VideoMerger(keyword=keyword if keyword else None, video_order=video_order, video_texts=video_texts, aspect_ratio=aspect_ratio, add_letterbox=add_letterbox)
        except Exception as e:
            logger.error(f"VideoMerger init error: {e}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'VideoMerger init failed: {str(e)}'
            }), 500
        
        # Check output_file
        if not hasattr(merger, 'output_file') or not merger.output_file:
            logger.error("merger.output_file not set.")
            return jsonify({
                'success': False,
                'message': 'Output file configuration error'
            }), 500
        
        output_filename = str(merger.output_file.name) if hasattr(merger.output_file, 'name') else str(merger.output_file)
        
        # Run in separate thread (async)
        def run_merge():
            try:
                logger.info(f"Start merge: keyword={keyword}, video_order={video_order}")
                merger.run()
                logger.info(f"Merge complete: {merger.output_file}")
            except Exception as e:
                logger.error(f"Merge execution error: {e}")
                logger.error(f"Detailed error: {traceback.format_exc()}")
        
        thread = threading.Thread(target=run_merge)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Video merge started.',
            'filename': output_filename
        })
    except Exception as e:
        logger.error(f"Merge request error: {e}")
        logger.error(f"Detailed error: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error occurred: {str(e)}'
        }), 500


@app.route('/api/upload/video', methods=['POST'])
def upload_video():
    """Upload video file (for merge)"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file found.'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected.'
            }), 400
        
        if not file.filename.lower().endswith('.mp4'):
            return jsonify({
                'success': False,
                'message': 'Only MP4 files are allowed.'
            }), 400
        
        # Save upload order with timestamp
        import time
        timestamp = int(time.time() * 1000)  # ms
        filename_base = os.path.basename(file.filename)
        # Allow alphanumeric, dot, dash, underscore
        safe_name = re.sub(r'[^\w\s\.\-_]', '', filename_base).strip()
        
        # Handle empty filename
        if not safe_name or safe_name == '.mp4':
            safe_name = 'video.mp4'
            
        # Ensure .mp4 extension
        if not safe_name.lower().endswith('.mp4'):
             safe_name = f"{safe_name}.mp4"
                
        filename = f"{timestamp:015d}_{safe_name}"
        
        raw_dir = Path("videos/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = raw_dir / filename
        file.save(str(file_path))
        
        return jsonify({
            'success': True,
            'message': 'File uploaded.',
            'filename': filename
        })
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return jsonify({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }), 500


@app.route('/api/upload/video/clear', methods=['POST'])
def clear_videos():
    """Delete all uploaded video files"""
    try:
        raw_dir = Path("videos/raw")
        
        deleted_count = 0
        if raw_dir.exists():
            for file in raw_dir.glob("*.mp4"):
                try:
                    file.unlink()  # Delete file
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"File delete failed {file.name}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} files deleted.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Clear failed: {str(e)}'
        }), 500


@app.route('/api/upload/video/delete', methods=['POST'])
def delete_video():
    """Delete a specific uploaded video file"""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'message': 'No filename provided.'
            }), 400
            
        # Security: prevent directory traversal
        filename = os.path.basename(filename)
        raw_dir = Path("videos/raw")
        file_path = raw_dir / filename
        
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return jsonify({
                'success': True,
                'message': f'File {filename} deleted.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'File not found.'
            }), 404
            
    except Exception as e:
        logger.error(f"File delete failed: {e}")
        return jsonify({
            'success': False,
            'message': f'Delete failed: {str(e)}'
        }), 500


@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video file (final folder)"""
    return send_from_directory('videos/final', filename)


@app.route('/api/download/<path:filename>')
def download_video(filename):
    """Download video file (final folder)"""
    return send_from_directory('videos/final', filename, as_attachment=True)


@app.route('/api/ai/generate-prompt', methods=['POST'])
def generate_ai_prompt():
    """Generate AI Prompt"""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        is_asmr = data.get('is_asmr', False)
        
        if not topic:
            return jsonify({
                'success': False,
                'message': 'Please enter a topic.'
            }), 400
        
        prompt_generator = PromptGenerator()
        result = prompt_generator.generate_prompt(topic)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error occurred: {str(e)}'
        }), 500


if __name__ == '__main__':
    # Create directories
    Path("videos/raw").mkdir(parents=True, exist_ok=True)
    Path("videos/final").mkdir(parents=True, exist_ok=True)

    Path("templates").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True)
    
    print("=" * 50)
    print("Short Video Auto-Merge Server")
    print("=" * 50)
    print("Open http://localhost:5001 in browser")
    print("=" * 50)
    
    import sys
    import warnings
    if not sys.warnoptions:
        warnings.simplefilter("ignore")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
    except Exception as e:
        logger.error(f"Server start failed: {e}")
        raise


