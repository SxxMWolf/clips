import os
import logging
import json
from typing import Dict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptGenerator:
    """극사실주의(Hyper-realistic) ASMR 먹방 영상 프롬프트 생성 서비스"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        # Gemini 2.0 Flash 모델 설정 (JSON 모드)
        self.model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config={"response_mime_type": "application/json"}
        )

    def generate_prompt(self, topic: str, add_credit: bool = True) -> Dict:
        logger.info(f"ASMR 먹방 프롬프트 생성 시작: {topic}")

        system_prompt = """
You are a professional ASMR video director specializing in hyper-realistic 'Visual Satisfaction' content.

TASK:
- Translate the Korean food name into a natural English culinary term.
- Describe the 'Satisfaction Point' of the food: (e.g., the crystalline crunch of sugar coating, the elastic stretch of cheese, the glistening oil on spicy sauce).

MANDATORY VIDEO RULES:
1. Framing: Extreme macro close-up shot focusing ONLY on a woman's lips and the food.
2. Appearance: Lips must have vivid, wet-look glossy red lipstick.
3. Physics: Highlight 'Subsurface Scattering' (light glowing through food) and 'Micro-textures' (salt grains, steam, or juice droplets).
4. Action: Video starts with the food touching the lips; follows with a slow-motion initial bite and rhythmic chewing.
5. Sound Context: No music/vocals. Visuals must imply loud, crisp, and wet ASMR sounds.
6. Specs: Vertical 9:16, Cinematic RAW, 4K, 60fps look.

Return JSON ONLY:
{
  "food_en": "English name",
  "satisfaction_detail": "sensory description of texture, light reflection, and physical reaction when bitten",
  "hook_caption": "short engaging question",
  "hashtags": ["#asmr", "#mukbang", "#satisfying", "#food", "#specific_keyword"]
}
"""

        user_prompt = f"Food (Korean): {topic}"

        try:
            response = self.model.generate_content(
                f"{system_prompt}\n\n{user_prompt}"
            )
            result = json.loads(response.text)

            food_en = result.get("food_en", topic)
            # 마침표 제거 후 프롬프트에 자연스럽게 삽입
            s_detail = result.get("satisfaction_detail", "").rstrip(".")

            video_prompt = (
                f"Hyper-realistic 4K ASMR video, 9:16 vertical format. "
                f"Extreme macro shot of a woman's lips with wet-look glossy red lipstick. "
                f"She is eating {food_en}. The scene captures {s_detail}. "
                f"Key visual elements: Subsurface scattering on the {food_en}, glistening highlights (catchlights) on the lips, "
                f"and micro-details of the food's texture. "
                f"The video begins with the {food_en} entering the mouth in slow motion, followed by vigorous, rhythmic chewing. "
                f"Shallow depth of field with a soft bokeh background. Cinematic RAW footage, natural studio lighting, "
                f"high contrast, no background music, pure focus on visual eating satisfaction."
            )

            hook_caption = result.get("hook_caption", "")
            if add_credit:
                hook_caption += "\n\n(inspired by pinterest. dm for credits)"

            return {
                "video_prompt": video_prompt,
                "hook_caption": hook_caption,
                "hashtags": self._finalize_hashtags(result.get("hashtags", []))
            }

        except Exception as e:
            logger.error(f"ASMR 프롬프트 생성 오류: {e}")
            return self._get_fallback_video(topic, add_credit)

    def _finalize_hashtags(self, tags: list) -> list:
        # #기호 정리 및 필수 태그 포함
        cleaned = [t if t.startswith("#") else f"#{t}" for t in tags]
        final = ["#fyp"]
        for t in cleaned:
            if t.lower() != "#fyp" and t not in final:
                final.append(t)
        return final[:5]

    def _get_fallback_video(self, topic, add_credit):
        return {
            "video_prompt": (
                f"Extreme close-up ASMR video of a woman eating {topic}. "
                f"9:16 vertical, red glossy lips, realistic textures, macro lens, 4K."
            ),
            "hook_caption": f"Is this your favorite? {topic}! \n\n(via Pinterest)",
            "hashtags": ["#fyp", "#asmr", "#mukbang", "#satisfying", "#food"]
        }

# --- 사용 예시 ---
if __name__ == "__main__":
    generator = PromptGenerator()
    # 예: '탕후루' 또는 '매운 치즈 불닭' 등 입력
    result = generator.generate_prompt("탕후루")
    
    print("--- 생성된 비디오 프롬프트 ---")
    print(result['video_prompt'])
    print("\n--- 캡션 및 해시태그 ---")
    print(result['hook_caption'])
    print(" ".join(result['hashtags']))