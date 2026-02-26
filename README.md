# Convivial Commons

Convivial Commons is a two-service FastAPI system for a multi-agent ecological parliament performance.

- **`convivial.py`** runs the AI debate flow.
- **`drama.py`** controls DMX motors/lights and receipt printing for the physical performance.
- **`perform.py`** is a utility API to trigger DMX channels manually for testing.
- **`topics.json`** contains selectable proposal topics.

## Architecture overview

1. A client calls `POST /start_discussion` on the Convivial API.
2. Convivial validates `topic_id` and asks Drama to begin with the selected prompt.
3. Convivial runs five character prompts via the OpenAI Responses API.
4. Convivial sends the full debate payload to Drama.
5. Drama runs the motor/light sequence and prints proposal, responses, and final vote.

## Repository layout

- `convivial.py` - AI/debate orchestrator service (`localhost:8000` suggested)
- `drama.py` - physical installation service (`localhost:9000` suggested)
- `perform.py` - DMX manual control utility (`localhost:9100` suggested)
- `agents.py` - all system prompts and `CHARACTERS` mapping
- `topics.json` - proposal list indexed by `id`
- `scripts/autostart/` - Raspberry Pi startup automation (systemd units + installer)

## Requirements

- Python 3.10+
- Raspberry Pi OS (for autostart scripts)
- OpenAI API key with access to Responses API
- Network access to:
  - Art-Net target (`255.255.255.255:6454` by default)
  - Optional network receipt printer (`192.168.1.251:9100` by default)
- Optional USB receipt printer compatible with `python-escpos`

## Setup

```bash
cd /workspace/convivial-commons
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn openai requests pydantic python-escpos
```

Set your API key:

```bash
export OPENAI_API_KEY="your_key_here"
```

## Run locally (manual)

Open separate terminals for each service.

### 1) Start Drama service

```bash
uvicorn drama:app --host 0.0.0.0 --port 9000
```

### 2) Start Convivial service

```bash
uvicorn convivial:app --host 0.0.0.0 --port 8000
```

### 3) (Optional) Start Perform utility

```bash
uvicorn perform:app --host 0.0.0.0 --port 9100
```

## API quick reference

### Convivial API (`:8000`)

- `POST /start_discussion`
  - Body:
    ```json
    { "topic_id": 1 }
    ```
  - Returns proposal, responses, votes, and decision.

### Drama API (`:9000`)

- `POST /start` with `{ "prompt": "..." }`
- `POST /add_response` with full debate payload
- `GET /is_running`

### Perform API (`:9100`)

- `POST /trigger` with `{ "number": 0..6 }`
  - `0` = all off
  - `1..5` = activate character channel
  - `6` = all on

---

## Raspberry Pi autostart (systemd)

This repo includes ready-to-use service units and an installer in `scripts/autostart`.

### Included files

- `scripts/autostart/convivial.service`
- `scripts/autostart/drama.service`
- `scripts/autostart/install_services.sh`

### What the installer does

- Creates `/etc/convivial-commons/convivial.env` if missing
- Copies service files into `/etc/systemd/system`
- Enables services to start automatically on boot
- Restarts `systemd` and starts both services immediately

### 1) Prepare environment file

Edit `/etc/convivial-commons/convivial.env` after first install:

```ini
OPENAI_API_KEY=replace_me
PHYSICAL_SERVER_URL=http://127.0.0.1:9000
```

> `PHYSICAL_SERVER_URL` is documented for consistency. `convivial.py` currently has this URL hardcoded, so update the Python file too if you change the port/host.

### 2) Install services

Run from the repository root:

```bash
chmod +x scripts/autostart/install_services.sh
sudo ./scripts/autostart/install_services.sh
```

### 3) Verify

```bash
systemctl status drama.service
systemctl status convivial.service
journalctl -u drama.service -f
journalctl -u convivial.service -f
```

### 4) Disable autostart (if needed)

```bash
sudo systemctl disable --now drama.service convivial.service
```

## Notes for production on Raspberry Pi

- Confirm the service user has permission to access USB printer devices.
- If your Art-Net interface is not broadcast-friendly, set a specific controller IP in `drama.py`.
- Consider pinning dependencies with a `requirements.txt` once hardware setup is stable.

## License

No license file is currently included in this repository.
