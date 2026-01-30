"""
GPT 기반 클립 선택 서비스
바이럴 잠재력이 높은 구간을 선택합니다.
"""

import os
import logging
from typing import List, Dict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClipSelector:
    """GPT를 사용한 클립 선택 서비스"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest', generation_config={"response_mime_type": "application/json"})
    
    def select_clips(
        self,
        transcript: List[Dict],
        user_prompt: str = "Find the most engaging and viral moments"
    ) -> List[Dict]:
        """
        GPT를 사용하여 바이럴 잠재력이 높은 클립을 선택합니다.
        
        Args:
            transcript: STT 결과 (start, end, text 포함)
            user_prompt: 사용자 프롬프트
            
        Returns:
            [
                {
                    "start": 120.5,
                    "end": 155.0,
                    "hook": "Unexpected revelation",
                    "confidence": 0.92
                },
                ...
            ]
        """
        logger.info(f"클립 선택 시작 (프롬프트: {user_prompt})")
        
        # 전체 텍스트 생성
        full_text = "\n".join([
            f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}"
            for seg in transcript
        ])
        
        # 비디오 길이 계산
        video_duration = max(seg["end"] for seg in transcript) if transcript else 0
        
        # GPT 프롬프트
        system_prompt = """You are a viral short-form video expert for YouTube Shorts, TikTok, and Instagram Reels.

Your task is to identify exactly 3 non-overlapping segments (15-45 seconds each) that have the highest viral potential.

IMPORTANT: The 3 segments must NOT overlap. Each segment must be completely separate from the others.

Focus on:
- Emotional spikes (surprise, shock, excitement)
- Strong hooks (attention-grabbing openings)
- Curiosity gaps (makes viewers want to know more)
- Controversial or surprising moments
- High engagement moments (statements that prompt comments)

Each segment must be:
- Between 15 and 45 seconds
- Self-contained (makes sense on its own)
- Has a clear hook or emotional peak
- Must NOT overlap with other segments

Return a JSON object with a "segments" array containing exactly 3 segments:
{
  "segments": [
    {
      "start": 120.5,
      "end": 155.0,
      "hook": "Unexpected revelation about the topic",
      "confidence": 0.92
    },
    {
      "start": 200.0,
      "end": 235.0,
      "hook": "Shocking moment",
      "confidence": 0.88
    },
    {
      "start": 300.0,
      "end": 330.0,
      "hook": "Engaging conclusion",
      "confidence": 0.85
    }
  ]
}

Do not include any other text, only the JSON object."""

        user_prompt_full = f"""Video transcript (duration: {video_duration:.1f}s):

{full_text}

User request: {user_prompt}

IMPORTANT: You must select exactly 3 non-overlapping viral segments. 
- Each segment should be 15-45 seconds
- They must NOT overlap with each other
- Spread them across the entire video duration if possible
- Focus on the most engaging moments

Return a JSON object with exactly 3 segments in the "segments" array."""

        try:
            prompt_content = f"{system_prompt}\n\n{user_prompt_full}"
            response = self.model.generate_content(prompt_content)
            
            # JSON 파싱
            import json
            result_text = response.text
            
            # JSON 파싱
            try:
                result_json = json.loads(result_text)
                # JSON 객체로 감싸져 있을 수 있음
                if "segments" in result_json:
                    clips = result_json["segments"]
                elif isinstance(result_json, list):
                    clips = result_json
                else:
                    # 단일 객체인 경우
                    clips = [result_json] if isinstance(result_json, dict) else []
            except json.JSONDecodeError:
                # 배열이 직접 반환된 경우 시도
                try:
                    clips = json.loads(result_text)
                    if not isinstance(clips, list):
                        clips = []
                except:
                    clips = []
            
            # 타임스탬프 검증 및 겹침 제거
            validated_clips = []
            for clip in clips:
                start = float(clip["start"])
                end = float(clip["end"])
                duration = end - start
                
                # 15-45초 범위 확인
                if 15 <= duration <= 45:
                    # 비디오 길이 내인지 확인
                    if 0 <= start < end <= video_duration:
                        validated_clips.append({
                            "start": start,
                            "end": end,
                            "hook": clip.get("hook", "Engaging moment"),
                            "confidence": float(clip.get("confidence", 0.8))
                        })
            
            # confidence로 정렬
            validated_clips.sort(key=lambda x: x["confidence"], reverse=True)
            
            # 겹치지 않는 클립 선택 (정확히 3개)
            non_overlapping_clips = self._select_non_overlapping(validated_clips, target_count=3)
            
            # 3개를 찾지 못한 경우, 더 관대한 조건으로 재시도
            if len(non_overlapping_clips) < 3 and len(validated_clips) > len(non_overlapping_clips):
                logger.warning(f"3개를 찾지 못함 ({len(non_overlapping_clips)}개만 선택됨). 더 관대한 조건으로 재시도...")
                # 작은 겹침은 허용 (5초 이내)
                non_overlapping_clips = self._select_non_overlapping_tolerant(validated_clips, target_count=3, tolerance=5.0)
            
            # 여전히 3개가 아니면 폴백 사용
            if len(non_overlapping_clips) < 3:
                logger.warning(f"3개를 찾지 못함. 폴백 로직 사용...")
                fallback_clips = self._fallback_selection(transcript, video_duration)
                # 폴백 결과와 기존 결과를 합쳐서 3개 만들기
                combined = non_overlapping_clips + fallback_clips
                # 중복 제거 및 정렬
                seen = set()
                unique_clips = []
                for clip in combined:
                    key = (round(clip["start"], 1), round(clip["end"], 1))
                    if key not in seen:
                        seen.add(key)
                        unique_clips.append(clip)
                    if len(unique_clips) >= 3:
                        break
                non_overlapping_clips = unique_clips[:3]
            
            logger.info(f"클립 선택 완료: {len(non_overlapping_clips)}개 (겹치지 않음)")
            return non_overlapping_clips
            
        except Exception as e:
            logger.error(f"GPT 클립 선택 오류: {e}")
            # 폴백: 간단한 휴리스틱 선택
            return self._fallback_selection(transcript, video_duration)
    
    def _select_non_overlapping(self, clips: List[Dict], target_count: int = 3) -> List[Dict]:
        """
        겹치지 않는 클립을 선택합니다.
        
        Args:
            clips: 검증된 클립 목록 (confidence로 정렬됨)
            target_count: 선택할 클립 개수 (기본 3개)
            
        Returns:
            겹치지 않는 클립 목록
        """
        if len(clips) == 0:
            return []
        
        selected = []
        
        for clip in clips:
            # 이미 선택된 클립과 겹치는지 확인
            overlaps = False
            for selected_clip in selected:
                # 겹침 확인: 두 구간이 겹치는 경우
                if not (clip["end"] <= selected_clip["start"] or clip["start"] >= selected_clip["end"]):
                    overlaps = True
                    break
            
            # 겹치지 않으면 추가
            if not overlaps:
                selected.append(clip)
                
                # 목표 개수에 도달하면 종료
                if len(selected) >= target_count:
                    break
        
        return selected
    
    def _select_non_overlapping_tolerant(self, clips: List[Dict], target_count: int = 3, tolerance: float = 5.0) -> List[Dict]:
        """
        작은 겹침을 허용하며 겹치지 않는 클립을 선택합니다.
        
        Args:
            clips: 검증된 클립 목록 (confidence로 정렬됨)
            target_count: 선택할 클립 개수 (기본 3개)
            tolerance: 허용할 겹침 시간 (초)
            
        Returns:
            겹치지 않는 클립 목록
        """
        if len(clips) == 0:
            return []
        
        selected = []
        
        for clip in clips:
            # 이미 선택된 클립과 겹치는지 확인 (tolerance 고려)
            overlaps = False
            for selected_clip in selected:
                # 겹침 확인: tolerance를 고려한 겹침 체크
                overlap_start = max(clip["start"], selected_clip["start"])
                overlap_end = min(clip["end"], selected_clip["end"])
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > tolerance:
                    overlaps = True
                    break
            
            # 겹치지 않으면 추가
            if not overlaps:
                selected.append(clip)
                
                # 목표 개수에 도달하면 종료
                if len(selected) >= target_count:
                    break
        
        return selected
    
    def _fallback_selection(self, transcript: List[Dict], duration: float) -> List[Dict]:
        """GPT 실패 시 폴백 선택 (간단한 휴리스틱) - 겹치지 않는 3개"""
        logger.warning("GPT 선택 실패, 휴리스틱 사용")
        
        clips = []
        segment_duration = 30  # 30초 클립
        
        # 비디오를 균등하게 3개 구간으로 나누기
        if duration >= 90:  # 최소 90초 필요 (30초 * 3)
            # 3개 구간으로 나누기
            segment_gap = (duration - (segment_duration * 3)) / 4  # 구간 사이 간격
            
            for i in range(3):
                start = segment_gap + i * (segment_duration + segment_gap)
                end = start + segment_duration
                
                if end <= duration:
                    clips.append({
                        "start": float(start),
                        "end": float(end),
                        "hook": f"Segment {i + 1}",
                        "confidence": 0.7
                    })
        else:
            # 짧은 영상의 경우 가능한 만큼만
            for i in range(0, int(duration), int(duration / 3)):
                start = float(i)
                end = min(start + segment_duration, duration)
                
                if end - start >= 15:  # 최소 15초
                    clips.append({
                        "start": start,
                        "end": end,
                        "hook": f"Segment {len(clips) + 1}",
                        "confidence": 0.7
                    })
                    
                    if len(clips) >= 3:
                        break
        
        return clips[:3]  # 정확히 3개 반환

