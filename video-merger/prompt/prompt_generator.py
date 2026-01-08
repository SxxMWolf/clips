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
    """극사실주의 ASMR 및 여행 콘텐츠를 위한 AI 프롬프트 생성 서비스"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=api_key)
    
    def generate_prompt(self, topic: str, add_credit: bool = True, prompt_type: str = "video") -> Dict:
        """주제에 대해 극사실주의 ASMR 프롬프트 또는 고양이 여행 프롬프트를 생성합니다."""
        
        if prompt_type == "cat_travel":
            return self.generate_cat_travel_prompt(topic, add_credit)
        
        logger.info(f"ASMR 비디오 프롬프트 생성 시작: {topic}")
        
        # ASMR의 시각적/청각적 질감을 극대화하는 시스템 프롬프트
        system_prompt = """You are a professional AI video director specializing in hyper-realistic ASMR cinematography.
Your goal is to describe a scene that looks like real RAW footage captured by a professional camera (Sony A7S III or Blackmagic Pocket Cinema Camera).

INSTRUCTIONS:
1. VIDEO PROMPT:
   - Focus on "Micro-details": Visible textures, moisture, skin pores, or material fibers.
   - Use "Macro photography" terms: Extreme close-up, shallow depth of field, blurred background.
   - Lighting: Use "Natural soft lighting" or "Clean studio light" to avoid a fake CGI look.
   - Audio Focus: Describe actions that imply crisp, satisfying sounds (tapping, slicing, pouring).
   - Format: Start with the action directly.

2. HOOK CAPTION:
   - A viral-style question to boost comments.
   - Short, punchy, and engaging.

3. HASHTAGS:
   - Always start with #fyp.
   - Total exactly 5 hashtags.

Return JSON:
{
  "video_detail": "Detailed description of the physical action and textures",
  "hook_caption": "Engaging question for social media",
  "hashtags": ["#fyp", "#asmr", "#satisfying", "#texture", "#macro"]
}"""

        user_prompt = f"Topic: {topic}\nGenerate a hyper-realistic ASMR video prompt."

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 사실감 극대화를 위한 기술적 키워드 결합
            video_detail = result.get("video_detail", topic).strip().rstrip('.')
            video_prompt = (
                f"Extreme macro RAW footage of {video_detail}. "
                f"Hyper-realistic textures, 4k resolution, shot on 100mm macro lens, "
                f"shallow depth of field, soft natural lighting, high frame rate. "
                f"Pure ASMR focus, no background music, crisp natural sounds, 4:5 aspect ratio."
            )
            
            # Hook caption 및 Credit 처리
            hook_caption = result.get("hook_caption", "")
            if add_credit:
                hook_caption += "\n\ninspired by pinterest. please dm me for credits"
            
            return {
                "video_prompt": video_prompt,
                "hook_caption": hook_caption,
                "hashtags": self._finalize_hashtags(result.get("hashtags", []))
            }
            
        except Exception as e:
            logger.error(f"오류 발생: {e}")
            return self._get_fallback_video(topic, add_credit)

    def generate_cat_travel_prompt(self, topic: str, add_credit: bool = True) -> Dict:
        """3고양이 여행의 극사실주의 사진 프롬프트를 생성합니다."""
        logger.info(f"고양이 여행 사진 프롬프트 생성 시작: {topic}")
        
        system_prompt = """You are an expert travel photographer. Create a prompt for a realistic photo of 3 specific cats (Orange Tabby, Calico, Tuxedo) wearing tan tactical backpacks.
The photo must look like a real smartphone or DSLR shot, not an illustration.

1. Describe the activity/location clearly.
2. Create a casual 'cat diary' caption in lowercase.
3. 5 hashtags: #fyp, #location, #cats, #travel, #country.

Return JSON:
{
  "activity": "exploring the cobblestone streets of Rome",
  "hook_caption": "we finally made it to rome! the pizza smells amazing... what should we eat next?",
  "hashtags": ["#fyp", "#Rome", "#cats", "#travel", "#Italy"]
}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Topic: {topic}"}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            activity = result.get("activity", topic)
            
            # 실제 카메라 데이터(EXIF) 스타일 프롬프트 구성
            cat_prompt = (
                f"A realistic professional travel photograph of three cats (an orange tabby, a calico, and a tuxedo) "
                f"wearing small detailed tan tactical backpacks, {activity}. "
                f"Shot on Fujifilm X-T4, 35mm lens, f/2.8, natural daylight, authentic travel photography style. "
                f"Real fur textures, sharp eyes, slight film grain, high resolution 8k, highly detailed background."
            )
            
            hook_caption = result.get("hook_caption", "")
            if add_credit:
                hook_caption += "\n\ninspired by pinterest. please dm me for credits"
            
            return {
                "video_prompt": cat_prompt,
                "hook_caption": hook_caption,
                "hashtags": self._finalize_hashtags(result.get("hashtags", []))
            }
        except Exception as e:
            logger.error(f"고양이 프롬프트 오류: {e}")
            return self._get_fallback_cat(topic, add_credit)

    def _finalize_hashtags(self, tags: list) -> list:
        """해시태그를 정리하여 항상 #fyp로 시작하는 5개 리스트로 반환합니다."""
        cleaned = [t if t.startswith("#") else f"#{t}" for t in tags]
        # #fyp 강제 추가 및 중복 제거
        final = ["#fyp"]
        for t in cleaned:
            if t.lower() != "#fyp" and t not in final:
                final.append(t)
        return final[:5]

    def _get_fallback_video(self, topic, add_credit):
        return {
            "video_prompt": f"Extreme close-up of {topic}, hyper-realistic, 4k, macro lens, no music, asmr style.",
            "hook_caption": f"Would you try this? {topic} is amazing!" + ("\n\ninspired by pinterest" if add_credit else ""),
            "hashtags": ["#fyp", "#asmr", "#satisfying", "#viral", "#foryou"]
        }

    def _get_fallback_cat(self, topic, add_credit):
        return {
            "video_prompt": f"Real photo of 3 cats with backpacks {topic}, shot on DSLR, 8k, realistic fur.",
            "hook_caption": f"we are traveling to {topic}! where next?" + ("\n\ninspired by pinterest" if add_credit else ""),
            "hashtags": ["#fyp", "#travel", "#cats", "#adventure", "#cute"]
        }

# 사용 예시
# generator = PromptGenerator()
# print(generator.generate_prompt("비누 조각하기", prompt_type="video"))