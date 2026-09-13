from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

for m in client.models.list():
    for action in m.supported_actions:
        if action == "generateContent":
            print(m.name)