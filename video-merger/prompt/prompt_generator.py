"""
AI 비디오/이미지 프롬프트 생성 서비스
바이럴 잠재력이 높은 프롬프트, 훅, 해시태그를 생성합니다.
"""

import os
import logging
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptGenerator:
    """AI 기반 프롬프트 생성 서비스"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=api_key)
    
    def generate_prompt(self, topic: str, add_credit: bool = True) -> Dict:
        """
        주제에 대한 AI 프롬프트, 훅, 해시태그를 생성합니다.
        
        Args:
            topic: 주제
            add_credit: 크레딧 멘트 추가 여부 (기본값: True)
            
        Returns:
            {
                "video_prompt": "...",
                "hook_caption": "...",
                "hashtags": ["#tag1", "#tag2", ...]
            }
        """
        logger.info(f"프롬프트 생성 시작: {topic}")
        
        system_prompt = """You are a professional AI video prompt influencer. Your job is to create prompts that look realistic, shocking, and viral.

When given a topic, generate:
1. An English AI video/image prompt that is simply a clear, well-structured English translation of the given topic. Make it easy to understand and suitable for AI video/image generation. Keep it simple and straightforward - just translate and refine the topic into good English.
2. A short hook-style caption that makes people comment. The caption MUST include a question that engages viewers and makes them want to comment. Examples:
   - "1 million dollars to cross the bridge. Which one are you choosing?"
   - "What is your favorite?"
   - "Would you do this? Comment below!"
   - "Which one would you pick?"
   The hook should present a choice, dilemma, or question that encourages engagement.
3. Exactly 5 relevant hashtags for TikTok/Reels/Shorts

IMPORTANT: The hashtags MUST ALWAYS include #fyp as the first hashtag. Then add exactly 4 additional relevant hashtags directly related to the topic/content. Keep them specific and relevant to the post content.

Focus on content that could realistically go viral. The hook caption should always end with a question or choice that makes viewers want to comment.

Return JSON format:
{
  "video_prompt": "Simple English translation of the topic, easy to understand",
  "hook_caption": "Short hook caption with engaging question here",
  "hashtags": ["#fyp", "#tag1", "#tag2", "#tag3", "#tag4"]
}"""

        user_prompt = f"Topic: {topic}\n\nGenerate the AI video prompt, hook caption, and viral hashtags."

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
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
            hashtags = result.get("hashtags", [])
            if isinstance(hashtags, str):
                hashtags = [tag.strip() for tag in hashtags.split(",")]
            
            # 해시태그에 # 추가 (없는 경우)
            hashtags = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in hashtags
            ]
            
            # 필수 해시태그: #fyp (항상 첫 번째)
            final_hashtags = []
            hashtags_lower = [tag.lower() for tag in hashtags]
            
            # #fyp가 없으면 첫 번째에 추가
            if "#fyp" not in hashtags_lower and "#fyp" not in [h.lower() for h in hashtags]:
                final_hashtags.append("#fyp")
            
            # 나머지 해시태그 추가 (중복 제거, #fyp는 제외하고 추가)
            for tag in hashtags:
                tag_lower = tag.lower()
                if tag_lower not in [t.lower() for t in final_hashtags] and tag_lower != "#fyp":
                    final_hashtags.append(tag)
            
            # #fyp가 있으면 첫 번째로 이동
            if "#fyp" in [h.lower() for h in final_hashtags]:
                final_hashtags = [h for h in final_hashtags if h.lower() != "#fyp"]
                final_hashtags.insert(0, "#fyp")
            elif "#fyp" not in [h.lower() for h in final_hashtags]:
                final_hashtags.insert(0, "#fyp")
            
            # Hook caption에 크레딧 멘트 추가 (옵션)
            hook_caption = result.get("hook_caption", "")
            if hook_caption and add_credit:
                # 이미 크레딧 멘트가 포함되어 있지 않으면 추가
                credit_text = "inspired by pinterest. please dm me for credits"
                if credit_text.lower() not in hook_caption.lower():
                    hook_caption = f"{hook_caption}\n\n{credit_text}"
            
            # Video prompt를 간단하게 정리: This is (주제) 형식으로 시작하고 필요한 지시사항만 추가
            video_prompt = result.get("video_prompt", "")
            if video_prompt:
                # 원본 프롬프트 정리
                video_prompt_clean = video_prompt.strip()
                
                # "This is", "It is", "This", "It"로 시작하는 경우 제거
                if video_prompt_clean.startswith("This is "):
                    video_prompt_clean = video_prompt_clean[8:]
                elif video_prompt_clean.startswith("It is "):
                    video_prompt_clean = video_prompt_clean[6:]
                elif video_prompt_clean.startswith("This "):
                    video_prompt_clean = video_prompt_clean[5:]
                elif video_prompt_clean.startswith("It "):
                    video_prompt_clean = video_prompt_clean[3:]
                
                # 마침표 제거
                video_prompt_clean = video_prompt_clean.rstrip('.')
                
                # "This is (주제)" 형식으로 시작
                video_prompt = f"This is {video_prompt_clean}."
                
                # 모든 프롬프트에 ASMR 중심, 노래 없이 추가
                video_prompt += " make an asmr-focused video with no music. make it hd. make the video as long as possible. in 9:16 aspect ratio."
            
            return {
                "video_prompt": video_prompt,
                "hook_caption": hook_caption,
                "hashtags": final_hashtags[:5]  # 정확히 5개 (#fyp 포함)
            }
            
        except Exception as e:
            logger.error(f"프롬프트 생성 오류: {e}")
            # 폴백
            hook_caption_fallback = f"You won't believe what happened with {topic}!"
            if add_credit:
                hook_caption_fallback += "\n\ninspired by pinterest. please dm me for credits"
            
            # 폴백도 항상 ASMR 중심
            fallback_prompt = f"This is {topic}. make an asmr-focused video with no music. make it hd. make the video as long as possible. in 9:16 aspect ratio."
            
            return {
                "video_prompt": fallback_prompt,
                "hook_caption": hook_caption_fallback,
                "hashtags": ["#fyp", "#viral", "#trending", "#shorts", "#foryou"][:5]  # 폴백도 5개
            }

