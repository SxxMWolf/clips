import os
import google.generativeai as genai
from dotenv import load_dotenv

def verify_gemini():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables.")
        print("Please check your .env file.")
        return False
    
    if api_key == "your_gemini_api_key_here":
        print("❌ GEMINI_API_KEY is still set to the placeholder value.")
        print("Please update .env with your actual API key.")
        return False

    print(f"✅ Found GEMINI_API_KEY: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("Testing API connection...")
        try:
            print("Listing available models...")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(m.name)
        except Exception as e:
            print(f"List models failed: {e}")

        # Try gemini-2.0-flash
        model_name = 'gemini-2.0-flash'
        print(f"Attempting to use model: {model_name}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, can you verify this API key works?")
        
        if response and response.text:
            print("✅ API Verification Successful!")
            print(f"Response: {response.text.strip()}")
            return True
        else:
            print("❌ API returned empty response.")
            return False
            
    except Exception as e:
        print(f"❌ API Verification Failed for {model_name}: {e}")
        return False

if __name__ == "__main__":
    verify_gemini()
