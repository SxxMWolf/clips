import os
import logging
import json
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptGenerator:
    """극사실주의(Hyper-realistic) ASMR 먹방 영상 프롬프트 생성 서비스"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def generate_prompt(self, topic: str, is_asmr: bool = False) -> Dict:
        logger.info(f"바이럴 비디오 프롬프트 생성 시작: {topic} (ASMR: {is_asmr})")

        if is_asmr:
            system_prompt = """
You are a Hyper-realistic ASMR Video Director.
Your goal is to generate a Commercial-grade ASMR video prompt based on the user's food input.

"Camera": "Extreme close-up of mouth, front view.",
"Subject": "Glossy red lips. No mics, headphones, or equipment.",
"Action": "A big mouthful of food enters mouth, immediate chewing.",
"Chewing": "Visible chewing textures, chew hard, the food texture is clearly visible between the teeth before swallowing.",
"Lighting": "Very bright studio light.",
"Audio": "ASMR sounds only, no music.",
"Quality": "8K hyper-realistic. No equipment visible.",
"Pacing": "Fast, continuous eating. NO slow motion. NO slowly. NO gentle pacing."
"Hashtags": ["#mukbang", "#asmr", "#food", "#eating"]
OUTPUT JSON FORMAT:
{
  "video_prompt": "Concise English prompt description. Focus on food and action. Include mandatory audio.",
  "hook_caption": "Short, engaging English caption.",
  "hashtags": ["#rainbow", "#mukbang", "#asmr", "#candy", "#chewingsounds", "#YourGeneratedTag1", "#YourGeneratedTag2"]
}
"""
        else:
            system_prompt = """
You are a Master Viral Video Director & Prompt Engineer.
Your goal is to generate the most visually stunning, high-retention video prompts for social media.

CRITICAL INSTRUCTION: 
**ALL OUTPUT MUST BE IN ENGLISH.** 
Even if the input is in Korean or another language, you MUST translate it and generate the prompt entirely in ENGLISH.

ANALYSIS PROTOCOL:
1. Translate the input topic to English (`topic_en`).
2. Determine the best category:
   - [FOOD]: Food/Drink -> 'Hyper-realistic Mukbang/ASMR'.
   - [ANIMAL]: Animal -> 'Cute/Cinematic/Funny'.
   - [GENERAL]: Other -> 'High-End Cinematic/Abstract/Tech'.

STYLE GUIDES:
[FOOD] -> "Extreme macro close-up, wet-look lips, subsurface scattering, rhythmic chewing."
[ANIMAL] -> "Wide aperture, golden hour lighting, soft fur texture, expressive eyes."
[GENERAL] -> "8K resolution, ray tracing, dramatic lighting, highly detailed."

OUTPUT FORMAT (JSON ONLY):
{
  "category": "FOOD" or "ANIMAL" or "GENERAL",
  "topic_en": "Translated English Topic",
  "visual_description": "Detailed prompt in ENGLISH describing the scene.",
  "hook_caption": "Engaging question in English (or mixed if appropriate for target).",
  "hashtags": ["#tag1", "#tag2"]
}
"""
        
        user_prompt = f"Topic/Food: {topic}"
        
        # 재시도 로직 (최대 3회)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
                
                if is_asmr:
                    # ASMR mode directly returns the prompt from logic
                    video_prompt = result.get("video_prompt", "")
                    
                    # 1. Force Negative Constraints if missing
                    neg_prompt = "No microphones, no headphones, no recording equipment visible."
                    if "No microphones" not in video_prompt:
                        video_prompt += f" {neg_prompt}"

                    # 3. Ensure audio disclaimer is present
                    # Removed 'mic perspective' to avoid potential visual confusion, used 'audio perspective'
                    required_audio = "high-fidelity ASMR chewing sounds, intimate close-up audio perspective, every bite clearly audible, no music, no vocals"
                    if "high-fidelity ASMR" not in video_prompt:
                         video_prompt += f", {required_audio}"
                    
                    # Ensure specific view constraint
                    asmr_view = "Extreme close-up of mouth, front view, chew hard."
                    if asmr_view not in video_prompt:
                        video_prompt = f"{asmr_view} {video_prompt}"
                else:
                    # Standard mode reconstruction
                    category = result.get("category", "GENERAL")
                    topic_en = result.get("topic_en", topic) 
                    visual_desc = result.get("visual_description", "")
                    
                    if category == "FOOD":
                        video_prompt = (
                            f"Hyper-realistic 4K ASMR, Extreme close-up of mouth, front view, chew hard. "
                            f"{visual_desc} "
                            f"Visual satisfaction. High contrast. No music. "
                            f"No microphones or equipment."
                        )
                    elif category == "ANIMAL":
                        video_prompt = (
                            f"Cute & Cinematic 4K video, 9:16 vertical. "
                            f"{visual_desc} "
                            f"Soft lighting, detailed textures, adorable expression. "
                            f"Shallow depth of field."
                        )
                    else:
                        video_prompt = (
                            f"Viral Cinematic 4K video, 9:16 vertical. "
                            f"{visual_desc} "
                            f"High production value, dynamic composition, trending visual style."
                        )

                # hook_caption = result.get("hook_caption", "")
                hook_caption = result.get("hook_caption", "")

                return {
                    "video_prompt": video_prompt,
                    "hook_caption": hook_caption,
                    "hashtags": self._finalize_hashtags(result.get("hashtags", []))
                }

            except Exception as e:
                logger.warning(f"프롬프트 생성 실패 (시도 {attempt+1}/{max_retries}): {e}")
                import time
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1)) # 지수 백오프
                else:
                    logger.error("최대 재시도 횟수 초과. Fallback 사용.")
                    return self._get_fallback_video(topic)

    def _finalize_hashtags(self, tags: list) -> list:
        cleaned = [t if t.startswith("#") else f"#{t}" for t in tags]
        final = []
        for t in cleaned:
            if t.lower() != "#fyp" and t not in final:
                final.append(t)
        return final[:10]

    def _get_fallback_video(self, topic):
        # Fallback에서도 가능한 영문 템플릿 사용 (번역 불가 시 어쩔 수 없음)
        return {
            "video_prompt": (
                f"Cinematic 4K video regarding '{topic}'. "
                f"9:16 vertical format, highly detailed, trending on artstation. "
                "(Note: API quota exceeded, using generic prompt)"
            ),
            "hook_caption": f"{topic} ✨",
            "hashtags": ["#viral", "#trending", "#shorts", "#video"]
        }

# --- 사용 예시 ---
if __name__ == "__main__":
    generator = PromptGenerator()
    
    test_topics = ["탕후루", "귀여운 고양이", "사이버펑크 서울"]
    
    for topic in test_topics:
        print(f"\n[Testing Topic: {topic}]")
        result = generator.generate_prompt(topic)
        print(f"Video Prompt: {result['video_prompt'][:100]}...")
        print(f"Hook: {result['hook_caption']}")