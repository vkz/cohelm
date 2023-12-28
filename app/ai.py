from openai import OpenAI
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

assistants = client.beta.assistants.list(
    order="desc",
    limit="20",
)

# assistants returns a json object {"object": "list", "data": [...]}. We want to find the assistant with the name "Colon" and store its id in assistant_id
assistant_id = None
for assistant in assistants.data:
    if assistant.name == "Colon":
        assistant_id = assistant.id
        break

# If we didn't find an assistant with the name "Colon", we need to create one
if assistant_id is None:
    assistant = client.beta.assistants.create(
        instructions="You are an insurance medical professional. You determine if the treatment plan in each medical record for a patient satisfies the guidelines for Colonoscopy",
        name="Colon",
        tools=[{"type": "retrieval"}],
        model="gpt-3.5-turbo-1106",
    )
    assistant_id = assistant.id
