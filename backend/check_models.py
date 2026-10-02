import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]

for name in MODELS:
    try:
        r = client.models.generate_content(model=name, contents="Say OK")
        print(f"WORKS     {name}")
    except Exception as e:
        code = getattr(e, "code", "?")
        print(f"FAILED    {name}  (code={code})")