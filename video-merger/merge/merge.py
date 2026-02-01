"""
Short Video Auto-Merge Module
Merges multiple short videos into one using FFmpeg.
Processes quickly without significant quality loss (tries to copy streams when possible, but re-encodes for consistency).
"""

import os
import subprocess
import logging
import shutil
import time
import tempfile
import json as json_lib
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from PIL import Image, ImageDraw, ImageFont

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoMerger:
    """Video Merger Class"""
    
    def __init__(self, keyword: str = None, video_order: list = None, video_texts: dict = None, aspect_ratio: str = '4:5', add_letterbox: bool = True):
        # Set paths based on parent directory
        BASE_DIR = Path(__file__).parent.parent
        self.raw_dir = BASE_DIR / "videos" / "raw"
        self.final_dir = BASE_DIR / "videos" / "final"
        self.video_order = video_order  # User defined order
        self.video_texts = video_texts or {}  # Footer text for each video {filename: text}
        self.aspect_ratio = aspect_ratio  # Output aspect ratio (e.g., '9:16', '16:9', '1:1')
        self.add_letterbox = add_letterbox  # Whether to add letterbox
        
        # Generate filename based on keyword
        if keyword:
            # Use keyword for filename (remove special chars)
            safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_keyword = safe_keyword.replace(' ', '_')
            if not safe_keyword:
                safe_keyword = "merged"
            # Add timestamp to prevent duplicates
            timestamp = int(time.time())
            filename = f"{safe_keyword}_{timestamp}.mp4"
        else:
            # Use timestamp only if no keyword
            timestamp = int(time.time())
            filename = f"merged_{timestamp}.mp4"
        
        self.output_file = self.final_dir / filename
        
        # Create directories
        self.final_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_files(self) -> list:
        """Get mp4 files from raw directory (sorted by user order or upload time)."""
        if not self.raw_dir.exists():
            logger.error(f"Directory not found: {self.raw_dir}")
            return []
        
        video_files = list(self.raw_dir.glob("*.mp4"))
        
        if not video_files:
            logger.warning(f"No mp4 files found in {self.raw_dir}.")
            return []
        
        # Sort by user defined order if provided
        if self.video_order and isinstance(self.video_order, list) and len(self.video_order) > 0:
            try:
                # Create dictionary with filename as key
                file_dict = {f.name: f for f in video_files}
                ordered_files = []
                
                # Add files in specified order
                for filename in self.video_order:
                    if filename in file_dict:
                        ordered_files.append(file_dict[filename])
                    else:
                        logger.warning(f"File in order list not found: {filename}")
                
                # Add remaining files sorted by timestamp
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
                
                # Use sorted files if available, otherwise use default
                if ordered_files:
                    video_files = ordered_files
                    logger.info(f"Sorted {len(video_files)} videos by user order:")
                else:
                    logger.warning("No files found matching user order, using default sort.")
            except Exception as e:
                logger.error(f"Error sorting by user order: {e}")
                logger.info("Using default sort.")
        else:
            # Sort by timestamp (upload order)
            # Filename format: {timestamp}_{original_filename} or {original_filename}
            def get_timestamp(filename):
                try:
                    # Extract timestamp from beginning of filename
                    parts = filename.stem.split('_')
                    if parts[0].isdigit() and len(parts[0]) >= 10:
                        return int(parts[0])
                    # Use file modification time if no timestamp
                    return int(filename.stat().st_mtime)
                except:
                    return int(filename.stat().st_mtime) if filename.exists() else 0
            
            video_files = sorted(video_files, key=get_timestamp, reverse=True)
            logger.info(f"Found {len(video_files)} videos (reverse sorted):")
        
        for i, video in enumerate(video_files, 1):
            display_name = video.name.split('_', 1)[1] if '_' in video.name else video.name
            logger.info(f"  {i}. {display_name}")
        
        return video_files
    
    def create_concat_file(self, video_files: list) -> str:
        """Create file list for FFmpeg concat."""
        concat_content = []
        
        for video_file in video_files:
            # Convert to absolute path
            abs_path = video_file.resolve()
            abs_path_str = str(abs_path)
            
            # Windows path handling
            abs_path_str = abs_path_str.replace('\\', '/')
            
            concat_content.append(f"file '{abs_path_str}'")
        
        # Create temporary file
        with NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('\n'.join(concat_content))
            concat_file_path = f.name
        
        logger.debug(f"Concat file created: {concat_file_path}")
        logger.debug(f"Concat content:\n{chr(10).join(concat_content)}")
        
        return concat_file_path
    
    def check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg is not installed or not in PATH.")
            logger.error("Installation guide: https://ffmpeg.org/download.html")
            return False
    
    def _render_text_overlay(self, text: str, width: int, height: int) -> str:
        """Render text (including emojis) to a transparent PNG file."""
        try:
            # Create a transparent image
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            lines = text.split('\n')
            
            # Font settings
            base_font_size = 60
            font_size = int(base_font_size * (height / 1920)) if height > 0 else base_font_size
            font_size = max(font_size, 48)
            
            # Load fonts
            font = None
            emoji_font = None
            
            # Primary font for text (Korean & Latin)
            regular_candidates = [
                "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf"
            ]
            
            for fp in regular_candidates:
                if os.path.exists(fp):
                    try:
                        font = ImageFont.truetype(fp, font_size, index=0) if fp.endswith('.ttc') else ImageFont.truetype(fp, font_size)
                        break
                    except: continue

            # Emoji font - try standard strike sizes (Apple Color Emoji is a bitmap font)
            # User requested 4x bigger emojis
            emoji_font_size = font_size * 4
            emoji_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
            if os.path.exists(emoji_path):
                # Try sizes around the requested 4x size
                # Common bitmap strikes are 20, 32, 40, 48, 64, 96, 128, 160
                strike_sizes = [emoji_font_size, 160, 128, 96, 64, 48]
                for sz in strike_sizes:
                    try:
                        emoji_font = ImageFont.truetype(emoji_path, int(sz), index=0)
                        break
                    except: continue
            
            if font is None:
                font = ImageFont.load_default()
            if emoji_font is None:
                emoji_font = font

            line_height = int(font_size * 1.5)
            base_y_offset = 250
            border_width = max(4, int(font_size / 12))
            
            def is_emoji(c):
                # Extended emoji and symbol range
                cp = ord(c)
                return cp > 0x2000 or (0x203C <= cp <= 0x3299)
            
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                
                y_pos = base_y_offset + idx * line_height
                
                # Calculate total width for centering
                # We render char by char or chunk by chunk to calculate width accurately
                total_w = 0
                max_char_h = 0
                for char in line:
                    f = emoji_font if is_emoji(char) else font
                    try:
                        left, top, right, bottom = draw.textbbox((0, 0), char, font=f)
                        total_w += (right - left)
                        max_char_h = max(max_char_h, bottom - top)
                    except:
                        w, h = draw.textsize(char, font=f)
                        total_w += w
                        max_char_h = max(max_char_h, h)
                
                x_cursor = (width - total_w) // 2
                
                # Center vertically relative to line height if emoji is much larger
                for char in line:
                    is_e = is_emoji(char)
                    f = emoji_font if is_e else font
                    
                    # Get char bbox for positioning
                    try:
                        left, top, right, bottom = draw.textbbox((0, 0), char, font=f)
                        char_w = right - left
                        char_h = bottom - top
                    except:
                        char_w, char_h = draw.textsize(char, font=f)
                    
                    # Vertical alignment: try to align middle-bottom
                    char_y = y_pos + (max_char_h - char_h) // 2 if is_e else y_pos
                    
                    if not is_e:
                        # Draw border for regular text only (emojis already have their own style)
                        for dx in range(-border_width, border_width + 1):
                            for dy in range(-border_width, border_width + 1):
                                if dx*dx + dy*dy <= border_width*border_width:
                                    draw.text((x_cursor + dx, char_y + dy), char, font=f, fill="black")
                    
                    # Draw char
                    draw.text((x_cursor, char_y), char, font=f, fill="white", embedded_color=is_e)
                    x_cursor += char_w
                
            # Create temp file
            temp_dir = self.raw_dir.parent
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.png',
                delete=False,
                dir=str(temp_dir)
            )
            temp_file.close()
            img.save(temp_file.name)
            logger.debug(f"Rendered overlay to {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to render text overlay: {e}")
            return None
            return None

    def merge_videos(self, video_files: list) -> bool:
        """Merge videos using FFmpeg."""
        if not video_files:
            logger.error("No videos to merge.")
            return False
            
        # Create concat file
        concat_file = self.create_concat_file(video_files)
        
        try:
            logger.info("Starting video merge...")
            
            # Get output format info from first video
            first_video = video_files[0]
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
                '-of', 'json',
                str(first_video)
            ]
            
            # Calculate target resolution based on aspect ratio
            aspect_parts = self.aspect_ratio.split(':')
            aspect_w = float(aspect_parts[0])
            aspect_h = float(aspect_parts[1])
            aspect_ratio_value = aspect_w / aspect_h
            
            # Base width
            base_width = 1080
            target_width = int(base_width)
            target_height = int(base_width / aspect_ratio_value)
            
            # Ensure target_height is even (required by libx264)
            if target_height % 2 != 0:
                target_height += 1
            
            logger.info(f"Target Aspect Ratio: {self.aspect_ratio} ({target_width}x{target_height})")
            
            # Check first video original resolution
            original_width, original_height = 1080, 1920
            try:
                probe_result = subprocess.run(
                    probe_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if probe_result.returncode == 0:
                    video_info = json_lib.loads(probe_result.stdout)
                    streams = video_info.get('streams', [])
                    if streams:
                        original_width = streams[0].get('width', 1080)
                        original_height = streams[0].get('height', 1920)
                        logger.info(f"Reference video info: {original_width}x{original_height}")
            except Exception as e:
                logger.warning(f"Failed to probe video info, using defaults: {e}")
            
            width, height = target_width, target_height
            
            # Use temp files for re-encoding
            temp_files = []
            
            try:
                logger.info("Re-encoding videos to common format...")
                overlay_temp_files = []
                for i, video_file in enumerate(video_files):
                    # Create temp file in videos directory
                    temp_dir = self.raw_dir.parent
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix='.mp4',
                        delete=False,
                        dir=str(temp_dir)
                    )
                    temp_file.close()
                    temp_file_path = Path(temp_file.name)
                    
                    if not temp_file_path.exists():
                        logger.error(f"Failed to create temp file: {temp_file_path}")
                        raise Exception(f"Failed to create temp file: {temp_file_path}")
                    temp_files.append(temp_file_path)
                    logger.debug(f"Temp file created: {temp_file_path}")
                    
                    # Prepare text overlay
                    video_filename = video_file.name
                    text_overlay = self.video_texts.get(video_filename, '')
                    
                    overlay_image_path = None
                    if text_overlay:
                        overlay_image_path = self._render_text_overlay(text_overlay, width, height)
                        if overlay_image_path:
                            overlay_temp_files.append(overlay_image_path)
                    
                    # Video filters setup
                    if self.add_letterbox:
                        # Letterbox: maintain aspect ratio, add black bars
                        video_filters = [
                            f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2',
                            f'pad={width}:{height}:({width}-iw)/2:({height}-ih)/2:color=black',
                            f'scale={width}:{height}',
                            'format=yuv420p'
                        ]
                    else:
                        # No letterbox: stretch to fit
                        video_filters = [
                            f'scale={width}:{height}:force_divisible_by=2',
                            'format=yuv420p'
                        ]
                    
                    vf_base = ','.join(video_filters)
                    
                    # FFmpeg encode command
                    encode_cmd = [
                        'ffmpeg',
                        '-i', str(video_file)
                    ]
                    
                    if overlay_image_path:
                        encode_cmd.extend(['-i', overlay_image_path])
                        # Filter complex: apply scaling/padding, then overlay
                        # User requested to last until the end instead of a few seconds
                        vf_complex = f"[0:v]{vf_base}[base];[1:v]format=rgba[over];[base][over]overlay=0:0"
                        encode_cmd.extend(['-filter_complex', vf_complex])
                    else:
                        encode_cmd.extend(['-vf', vf_base])
                    
                    encode_cmd.extend([
                        '-c:v', 'libx264',
                        '-preset', 'veryslow',
                        '-crf', '10',  # High quality
                        '-profile:v', 'high',
                        '-level', '4.2',
                        '-r', '30',
                        '-pix_fmt', 'yuv420p',
                        '-tune', 'film',
                        '-x264-params', 'keyint=60:min-keyint=60:scenecut=0:aq-mode=3:aq-strength=1.0:merange=24:subme=10:trellis=2',
                        '-c:a', 'aac',
                        '-b:a', '320k',
                        '-y',
                        str(temp_file_path)
                    ])
                    
                    encode_result = subprocess.run(
                        encode_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if encode_result.returncode != 0:
                        logger.error(f"Failed to re-encode video {i+1}: {encode_result.stderr}")
                        raise Exception(f"Failed to re-encode video {i+1}")
                    
                    if not temp_file_path.exists():
                        raise Exception(f"Re-encoded video missing: {temp_file_path}")
                    
                    file_size = temp_file_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Re-encoded video {i+1}/{len(video_files)} (Size: {file_size:.2f} MB)")
                
                # Check all temp files
                for temp_file in temp_files:
                    if not temp_file.exists() or temp_file.stat().st_size == 0:
                        raise Exception(f"Temp file invalid: {temp_file}")
                
                # Create normalized concat file
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
                    logger.debug(f"Added to concat: {abs_path_str}")
                
                concat_file_normalized.close()
                concat_file_path = concat_file_normalized.name
                
                # Final merge using concat demuxer
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file_path,
                    '-c', 'copy',  # Stream copy
                    '-movflags', '+faststart',
                    '-y',
                    str(self.output_file)
                ]
                
                logger.info(f"Executing merge command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0:
                    file_size = self.output_file.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ Merge Complete: {self.output_file}")
                    logger.info(f"   Total Size: {file_size:.2f} MB")
                    return True
                else:
                    logger.error(f"❌ Merge Failed:")
                    logger.error(result.stderr)
                    return False
                    
            finally:
                # Cleanup temp files
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
                for overlay_file in overlay_temp_files:
                    try:
                        if os.path.exists(overlay_file):
                            os.unlink(overlay_file)
                    except:
                        pass
                
        except Exception as e:
            logger.error(f"Error during video merge: {e}")
            return False
        finally:
            try:
                os.unlink(concat_file)
            except:
                pass
    
    def run(self):
        """Run the full merge process."""
        logger.info("=" * 50)
        logger.info("Starting Short Video Merge")
        logger.info("=" * 50)
        
        # Check FFmpeg
        if not self.check_ffmpeg():
            return
        
        # Get video files
        video_files = self.get_video_files()
        
        if not video_files:
            return
        
        # Execute merge
        success = self.merge_videos(video_files)
        
        if success:
            logger.info("=" * 50)
            logger.info("Merge Process Finished Successfully")
            logger.info("=" * 50)
        else:
            logger.error("Merge Process Failed")


if __name__ == "__main__":
    merger = VideoMerger()
    merger.run()
