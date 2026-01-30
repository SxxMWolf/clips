import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Use the hardcoded key if env var not found (though best practice is env var)
    # But for this test let's rely on .env
    pass

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash-lite-001') # trying the 001 version to be specific or 'gemini-2.0-flash-lite'
try:
    response = model.generate_content("Hello")
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
