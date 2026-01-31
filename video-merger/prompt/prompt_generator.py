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

    def generate_prompt(self, topic: str, add_credit: bool = True, is_asmr: bool = False) -> Dict:
        logger.info(f"바이럴 비디오 프롬프트 생성 시작: {topic} (ASMR: {is_asmr})")

        if is_asmr:
            system_prompt = """
You are a Hyper-realistic ASMR Video Director.
Your goal is to generate a Commercial-grade ASMR video prompt based on the user's food input.

"Camera": "Strictly front-facing, fixed camera, extreme macro close-up of lips and mouth only, blurred background.",
"Subject": "Female with red glossy lipstick and strong catchlight on lips and food, commercial-grade.",
"Action": "Video starts with food entering the mouth from the front. Immediate biting, fast continuous eating.",
"Chewing": "Teeth clamp down firmly. Food is crushed between teeth. Multiple quick bite-and-crush cycles.",
"Sound_Visuals": "Visualized crunch, crack, shatter, stretch, and juice burst through fractures, snaps, pulls, and liquid release.",
"Lighting": "Pure white studio light, high contrast.",
"Audio": "High-fidelity binaural ASMR chewing. Wet, sticky, crunchy textures. No music or vocals.",
"Quality": "Ultra-realistic, 8K, lifelike motion with realistic food deformation.",
"Hashtags": ["#rainbow", "#mukbang", "#asmr", "#candy", "#chewingsounds"]
OUTPUT JSON FORMAT:
{
  "video_prompt": "Combine ALL the above rules into a single continuous English prompt description. Ensure the specific food is the star. Include the mandatory audio prompt at the end.",
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
                    # Ensure audio disclaimer is present if not
                    required_audio = "high-fidelity ASMR chewing sounds, intimate close-up mic perspective, every bite clearly audible, no music, no vocals"
                    if required_audio not in video_prompt:
                         video_prompt += f", {required_audio}"
                else:
                    # Standard mode reconstruction
                    category = result.get("category", "GENERAL")
                    topic_en = result.get("topic_en", topic) 
                    visual_desc = result.get("visual_description", "")
                    
                    if category == "FOOD":
                        video_prompt = (
                            f"Hyper-realistic 4K ASMR video, 9:16 vertical. "
                            f"{visual_desc} "
                            f"Focus on visual satisfaction, big appetite. "
                            f"Cinematic lighting, high contrast, no background music."
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

                hook_caption = result.get("hook_caption", "")
                # if add_credit:
                #    hook_caption += "\n\n(inspired by pinterest. dm for credits)"

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
                    return self._get_fallback_video(topic, add_credit)

    def _finalize_hashtags(self, tags: list) -> list:
        cleaned = [t if t.startswith("#") else f"#{t}" for t in tags]
        final = ["#fyp"]
        for t in cleaned:
            if t.lower() != "#fyp" and t not in final:
                final.append(t)
        return final[:10]

    def _get_fallback_video(self, topic, add_credit):
        # Fallback에서도 가능한 영문 템플릿 사용 (번역 불가 시 어쩔 수 없음)
        return {
            "video_prompt": (
                f"Cinematic 4K video regarding '{topic}'. "
                f"9:16 vertical format, highly detailed, trending on artstation. "
                "(Note: API quota exceeded, using generic prompt)"
            ),
            "hook_caption": f"{topic} ✨",
            "hashtags": ["#fyp", "#viral", "#trending", "#shorts", "#video"]
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