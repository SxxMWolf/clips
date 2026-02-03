import os
import logging
import json
import time
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptGenerator:
    """극사실주의(Hyper-realistic) ASMR 먹방 영상 프롬프트 생성 서비스 (ASMR 전용)"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def generate_prompt(self, topic: str, is_asmr: bool = True) -> Dict:
        logger.info(f"ASMR 프롬프트 생성 시작: {topic}")

        system_prompt = """
You are a Hyper-realistic ASMR Video Director.
Your goal is to generate a Commercial-grade ASMR mukbang video prompt.

CAMERA:
Extreme macro close-up of mouth only, strictly front-facing, fixed camera.

SUBJECT:
Glossy red lips, wet look, strong catchlight.

ACTION:
Large mouthful enters mouth from the front.

LIGHTING:
Very bright studio lighting, high contrast.

PACING:
Fast, continuous eating.
NO slow motion. NO slowly. NO gentle pacing.

QUALITY:
8K hyper-realistic, commercial-grade.

OUTPUT JSON FORMAT:
{
  "video_prompt": "Concentrate on describing the food's appearance and the visual interaction with the mouth.",
  "hook_caption": "Short, engaging English caption.",
  "hashtags": ["#mukbang", "#asmr", "#food", "#chewing", "#teethsounds"]
}
"""
        
        user_prompt = f"Topic/Food: {topic}"
        
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
                video_prompt = result.get("video_prompt", "")

                # ✅ 씹기 강제 (Teeth contact & Aggressive chewing)
                force_chewing = (
                    "Teeth fully closing on every bite, strong jaw compression, aggressive chewing. "
                    "Upper and lower teeth make full contact. "
                    "Food crushed visibly between teeth."
                )
                video_prompt = f"{force_chewing} {video_prompt}"

                # ✅ 장비 없음 제약 (후처리)
                video_prompt += " No recording equipment visible."

                # ✅ 오디오 강화
                video_prompt += (
                    " Intimate close-up ASMR chewing sounds, "
                    "every bite clearly audible. No music. No vocals."
                )

                return {
                    "video_prompt": video_prompt,
                    "hook_caption": result.get("hook_caption", ""),
                    "hashtags": self._finalize_hashtags(result.get("hashtags", []))
                }

            except Exception as e:
                logger.warning(f"프롬프트 생성 실패 (시도 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    logger.error("최대 재시도 초과. Fallback 사용.")
                    return self._get_fallback_video(topic)

    def _finalize_hashtags(self, tags: list) -> list:
        cleaned = [t if t.startswith("#") else f"#{t}" for t in tags]
        final = []
        for t in cleaned:
            if t.lower() != "#fyp" and t not in final:
                final.append(t)
        return final[:10]

    def _get_fallback_video(self, topic):
        return {
            "video_prompt": (
                f"Hyper-realistic ASMR mukbang of {topic}. "
                "Extreme close-up of mouth, teeth fully closing, aggressive chewing. "
                "No recording equipment visible. "
                "Intimate close-up ASMR chewing sounds."
            ),
            "hook_caption": "Can you hear every bite?",
            "hashtags": ["#asmr", "#mukbang", "#chewing", "#satisfying"]
        }

# --- 사용 예시 ---
if __name__ == "__main__":
    generator = PromptGenerator()
    result = generator.generate_prompt("망고 씹어먹기")
    print(f"Video Prompt: {result['video_prompt']}")
    print(f"Hook: {result['hook_caption']}")
    print(f"Hashtags: {result['hashtags']}")
