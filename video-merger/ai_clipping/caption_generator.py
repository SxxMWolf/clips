import os
import logging
import json
from typing import Dict, List
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaptionGenerator:
    """AI 기반 바이럴 제목 및 소셜 미디어 메타데이터 생성 서비스"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        # 최신 모델인 gemini-2.0-flash 사용 및 JSON 모드 강제
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash', 
            generation_config={"response_mime_type": "application/json"}
        )
    
    def generate_caption(self, clip_text: str, hook: str) -> Dict:
        """
        클립의 내용을 분석하여 바이럴 잠재력이 높은 제목, 설명, 해시태그를 생성합니다.
        """
        logger.info("바이럴 캡션 및 메타데이터 생성 시작")
        
        system_prompt = """
You are a top-tier social media strategist for TikTok, Instagram Reels, and YouTube Shorts.
Your goal is to stop the scroll and maximize shareability.

STRATEGY:
- Title: Use 'Curiosity Gaps' or 'High Stakes' (e.g., "I didn't expect this...", "The secret to...").
- Hook Integration: Seamlessly blend the provided 'hook reason' into the title and description.
- Tone: High energy, punchy, and authentic.
- Audience: Global English-speaking audience.

OUTPUT SPECIFICATIONS:
1. Title: Emotional, provocative, or intriguing. Max 80 characters. Use emojis strategically.
2. Description: 2-3 power sentences. Include a Call-to-Action (CTA) like "Share this with a friend who needs to see this".
3. Hashtags: 15-20 highly relevant tags. Mix of:
   - Viral Broad (e.g., #fyp, #viral)
   - Content Specific (e.g., #cookinghacks, #mindset)
   - Action Oriented (e.g., #watchthis, #dontblink)

Return JSON ONLY in this format:
{
  "title": "Viral Title Here 😱",
  "description": "Powerful description with CTA.",
  "hashtags": ["#tag1", "#tag2", "#tag3"]
}
"""

        user_prompt = f"""
[Clip Content Analysis]:
{clip_text}

[Why this clip is a hook]:
{hook}

Generate the viral metadata now.
"""

        try:
            response = self.model.generate_content(f"{system_prompt}\n\n{user_prompt}")
            result = json.loads(response.text)
            
            # 해시태그 가공 및 정제
            raw_hashtags = result.get("hashtags", [])
            refined_hashtags = self._clean_hashtags(raw_hashtags)
            
            return {
                "title": result.get("title", "Wait for it... 😲"),
                "description": result.get("description", "You won't believe what happens next. Check it out!"),
                "hashtags": refined_hashtags[:20] # 최대 20개로 제한 (알고리즘 최적화)
            }
            
        except Exception as e:
            logger.error(f"캡션 생성 중 오류 발생: {e}")
            return self._get_fallback_metadata(hook)

    def _clean_hashtags(self, tags: List[str]) -> List[str]:
        """해시태그 형식 정리 및 중복 제거"""
        cleaned = []
        for tag in tags:
            # 공백 제거 및 # 기호 강제
            t = tag.strip().replace(" ", "")
            if not t.startswith("#"):
                t = f"#{t}"
            if t not in cleaned and len(t) > 1:
                cleaned.append(t)
        return cleaned

    def _get_fallback_metadata(self, hook: str) -> Dict:
        """오류 발생 시 반환할 최소한의 데이터"""
        return {
            "title": f"You need to see this: {hook[:50]}...",
            "description": "This clip is viral for a reason. Watch until the end! #viral #shorts",
            "hashtags": ["#fyp", "#viral", "#trending", "#shorts", "#foryou"]
        }

# --- 실행 예시 ---
if __name__ == "__main__":
    generator = CaptionGenerator()
    
    # 예시 데이터
    sample_text = "How to make a 5-minute pasta that tastes like a 5-star restaurant."
    sample_hook = "The secret ingredient revealed at the end is completely unexpected."
    
    result = generator.generate_caption(sample_text, sample_hook)
    
    print(f"TITLE: {result['title']}")
    print(f"DESC: {result['description']}")
    print(f"TAGS: {' '.join(result['hashtags'])}")