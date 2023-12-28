from openai import OpenAI
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import time
import json

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# In browser reload https://platform.openai.com/assistants and grab Authorisation Bearer SESSION_KEY from the network tab for request assistants?limit=10
sess_key = os.getenv("OPENAI_SESSION_KEY")
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


def upload_file(file_hash):
    # Check if the file has already been uploaded to OpenAI
    files = client.beta.files.list(purpose="assistants")

    file_id = None
    for file in files.data:
        if file.filename == file_hash + ".pdf":
            file_id = file.id
            break

    # If the file hasn't been uploaded to OpenAI, upload it
    if file_id is None:
        file = client.files.create(
            file=open(os.path.join("uploads", file_hash + ".pdf"), "rb"),
            purpose="assistants",
        )
        file_id = file.id

    # Now write file.id to uploads/file_hash.id
    with open(os.path.join("uploads", file_hash + ".id"), "w+") as file:
        file.write(file_id)

    return file_id


def create_thread(file_hash):
    # First, upload the file if it hasn't been uploaded already
    file_id = upload_file(file_hash)

    # Now create a new thread
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "Here is a medical record for a patient with a treatment plan and medical history.",
                "file_ids": [file_id],
            }
        ],
        metadata={"file": file_hash},
    )

    with open(os.path.join("uploads", file_hash + ".threads"), "a") as file:
        file.write(thread.id + "\n")

    return thread.id


# TODO oh great their the SDK doesn't support the /v1/threads endpoint yet and no way to get a list of threads. Going directttly to the endpoint requires a browser session token not API key - morons
def threads(delete=False):
    url = "https://api.openai.com/v1/threads"
    headers = {
        "Authorization": "Bearer " + sess_key,
        "OpenAI-Beta": "assistants=v1",
    }
    response = requests.get(url, headers=headers)
    if delete:
        ids = [t["id"] for t in response.json()["data"]]
        for id in ids:
            print("Deleting thread " + id)
            client.beta.threads.delete(id)
            time.sleep(1)
    return response.json()


# threads(delete=True)
# print(threads())


def run_prompt(thread_id=None, prompt_path=None):
    if thread_id is None or prompt_path is None:
        raise Exception("expected thread_id and prompt_path")

    prompt = ""
    with open(prompt_path, "r") as file:
        prompt = file.read()

    # enqueue the prompt
    client.beta.threads.messages.create(
        thread_id,
        role="user",
        content=prompt,
    )

    # start a run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    # poor man's polling
    while run.status != "complete":
        time.sleep(3)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if (
            run.status == "failed"
            or run.status == "cancelled"
            or run.status == "expired"
        ):
            return f"Run failed for {prompt_path}: assistant run failed"

    # return last assistant message
    messages = client.beta.threads.messages.list(thread_id).data

    # get the last message from the assistant
    reply = messages[-1]
    reply_text = reply.content[0].text.value

    if reply.role != "assistant":
        return f"Run failed for {prompt_path}: assistant did not reply"

    # poor man's validation by parsing the result as JSON
    try:
        reply_json = json.loads(reply_text)
        json.dumps(reply_json, indent=4)
        return reply_text
    except json.JSONDecodeError:
        return f"Run failed for {prompt_path}: assistant replied with invalid JSON"


def prompt_cpt_codes(thread_id):
    run_prompt(thread_id=thread_id, prompt_path="prompts/cpt.prompt")


def prompt_conservative_treatment(thread_id):
    run_prompt(thread_id=thread_id, prompt_path="prompts/conservative.prompt")


def prompt_guidelines(thread_id):
    run_prompt(thread_id=thread_id, prompt_path="prompts/guidelines.prompt")
