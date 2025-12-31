"""
AI 제목/해시태그 생성 서비스
바이럴 잠재력이 높은 제목과 해시태그를 생성합니다.
"""

import os
import logging
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptionGenerator:
    """AI 기반 제목/해시태그 생성 서비스"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=api_key)
    
    def generate_caption(
        self,
        clip_text: str,
        hook: str
    ) -> Dict:
        """
        클립용 제목, 해시태그, 설명을 생성합니다.
        
        Args:
            clip_text: 클립의 텍스트 내용
            hook: 클립의 훅 (왜 선택되었는지)
            
        Returns:
            {
                "title": "Shocking revelation about...",
                "hashtags": ["#shorts", "#viral", ...],
                "description": "..."
            }
        """
        logger.info("제목/해시태그 생성 시작")
        
        system_prompt = """You are a viral content expert for YouTube Shorts, TikTok, and Instagram Reels.

Generate engaging titles and hashtags that:
- Maximize curiosity and click-through rate
- Encourage comments and engagement
- Are honest (not clickbait lies)
- Optimize for retention
- Are suitable for English-speaking audiences

Title requirements:
- Maximum 80 characters
- Attention-grabbing hook
- Creates curiosity gap
- Makes viewers want to watch

Hashtags requirements:
- 15-25 hashtags
- Mix of broad and niche tags
- Trending when possible
- Platform-appropriate"""

        user_prompt = f"""Clip content:
{clip_text}

Hook reason: {hook}

Generate:
1. A viral title (max 80 chars)
2. 15-25 hashtags (comma-separated)
3. A short description (2-3 sentences)

Return JSON format:
{{
  "title": "...",
  "hashtags": ["#tag1", "#tag2", ...],
  "description": "..."
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # response_format 지원 모델
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # 해시태그 정리
            if isinstance(result.get("hashtags"), str):
                hashtags = [tag.strip() for tag in result["hashtags"].split(",")]
            else:
                hashtags = result.get("hashtags", [])
            
            # 해시태그에 # 추가 (없는 경우)
            hashtags = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in hashtags
            ]
            
            return {
                "title": result.get("title", "Viral Clip"),
                "hashtags": hashtags[:25],  # 최대 25개
                "description": result.get("description", "")
            }
            
        except Exception as e:
            logger.error(f"제목/해시태그 생성 오류: {e}")
            # 폴백
            return {
                "title": hook[:80] if hook else "Viral Clip",
                "hashtags": ["#shorts", "#viral", "#trending", "#fyp", "#foryou"],
                "description": clip_text[:200] if clip_text else ""
            }

