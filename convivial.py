from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from agents import CHARACTERS
import requests
import json

PHYSICAL_SERVER_URL = "http://127.0.0.1:9000"

client = OpenAI()
app = FastAPI()

# ---------------- LOAD TOPICS ----------------

with open("topics.json", "r", encoding="utf-8") as f:
    TOPICS = json.load(f)["topics"]

# Create quick lookup dictionary
TOPIC_LOOKUP = {item["id"]: item["topic"] for item in TOPICS}

class DebateRequest(BaseModel):
    topic_id: int  # â now sending only a number

conversation_log = []

# ---------------- DRAMA SERVER HELPERS ----------------
                                                                                                    
def drama_is_running() -> bool:
    try:
        r = requests.get(f"{PHYSICAL_SERVER_URL}/is_running", timeout=2)
        return r.json().get("running", False)
    except:
        return False

def drama_start(prompt: str):
    try:
        r = requests.post(
            f"{PHYSICAL_SERVER_URL}/start",
            json={"prompt": prompt},   #  send prompt to physical server
            timeout=2
        )
        r.raise_for_status()
        print("[Drama] Performance started with prompt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drama server start failed: {e}")


def drama_send_response(payload: dict):
    try:
        r = requests.post(
            f"{PHYSICAL_SERVER_URL}/add_response",
            json=payload,
            timeout=5
        )
        r.raise_for_status()
        print("[Drama] Debate payload sent")
    except Exception as e:
        print(f"[Drama error] {e}")

# ---------------- AGENT RUNNER ----------------

def run_agent(system_prompt, topic, history):
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {
            "role": "user",
            "content": """You are part of a 5-agent debate system debating a human proposal.
Congress members:
Network of Water â water bodies of Kochi
Rain Tree â urban flora
Indian Rock Python â endemic fauna
Brown-headed Gull â migratory fauna
Pearl Spot â local aquatic food source

Rules:
1. Begin with your check-in phrase.
2. Give a succinct reaction explaining how it affects you.
3. Be emotional but fact-based.
4. Vote only on the proposal in its current form.

End your response with exactly one line:
VOTE: YES or VOTE: NO"""
        }
    ]

    res = client.responses.create(
        model="gpt-5.1",
        input=messages,
        max_output_tokens=400
    )

    return res.output_text.strip()

# ---------------- API ----------------

@app.post("/start_discussion")
def start_discussion(req: DebateRequest):
    global conversation_log

    # â Validate topic_id
    if req.topic_id not in TOPIC_LOOKUP:
        raise HTTPException(status_code=400, detail="Invalid topic_id")

    selected_topic = TOPIC_LOOKUP[req.topic_id]

    # â Reject if drama server busy
    if drama_is_running():
        raise HTTPException(
            status_code=409,
            detail="Drama server is currently running a performance"
        )

    # â¶ Start drama
    drama_start(selected_topic)

    conversation_log = []
    results = {}
    votes = {"YES": 0, "NO": 0}

    conversation_log.append({
        "role": "user",
        "content": selected_topic
    })

    for name, prompt in CHARACTERS.items():
        reply = run_agent(prompt, selected_topic, conversation_log)

        conversation_log.append({
            "role": "assistant",
            "content": f"{name.upper()}: {reply}"
        })

        results[name] = reply

        if reply.endswith("VOTE: YES"):
            votes["YES"] += 1
        elif reply.endswith("VOTE: NO"):
            votes["NO"] += 1

    decision = "PASSED" if votes["YES"] > votes["NO"] else "REJECTED"

    payload = {
        "proposal_id": req.topic_id,
        "proposal": selected_topic,
        "conversation": conversation_log,
        "responses": results,
        "votes": votes,
        "decision": decision
    }

    drama_send_response(payload)

    return payload
