from fastapi import FastAPI
from pydantic import BaseModel
import socket
import time
import threading
from escpos.printer import Usb, Network

app = FastAPI()

# ---------------- DMX CONFIG ----------------

MIN_SYNC_TIME = 15
CHARACTER_TIME = 10
PAUSE_TIME = 3

ARTNET_PORT = 6454
ARTNET_IP = "255.255.255.255"

MOTOR_ON = 21
MOTOR_OFF = 0

LIGHT_ON = 255
LIGHT_OFF = 0

# Motor â Agent mapping
CHANNEL_AGENT_MAP = {
    1: "Karimeen",
    2: "Brown Headed Gull",
    3: "Rock Python",
    4: "Raintree",
    5: "Water Network"
}

# Motor â Light mapping
CHANNEL_LIGHT_MAP = {
    1: 10,
    2: 20,
    3: 30,
    4: 40,
    5: 50
}

CHANNELS = list(CHANNEL_AGENT_MAP.keys())

# ---------------- SOCKET ----------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# ---------------- DMX STATE ----------------

dmx_data = bytearray(512)


def send_universe():
    packet = bytearray(18 + 512)

    packet[0:7] = b'Art-Net'
    packet[7] = 0x00
    packet[8] = 0x00
    packet[9] = 0x50
    packet[10] = 0x00
    packet[11] = 14
    packet[12] = 0x00
    packet[13] = 0x00
    packet[14] = 0x00
    packet[15] = 0x00
    packet[16] = 0x02
    packet[17] = 0x00

    packet[18:] = dmx_data

    sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))


def all_off():
    print("[DMX] All OFF")

    # Motors OFF
    for ch in CHANNELS:
        dmx_data[ch - 1] = MOTOR_OFF

    # Lights OFF
    for motor_ch, light_ch in CHANNEL_LIGHT_MAP.items():
        dmx_data[light_ch - 1] = LIGHT_OFF

    send_universe()


def all_on():
    print("[DMX] All ON (sync phase)")

    # Motors ON
    for ch in CHANNELS:
        dmx_data[ch - 1] = MOTOR_ON

    # Lights ON
    for motor_ch, light_ch in CHANNEL_LIGHT_MAP.items():
        dmx_data[light_ch - 1] = LIGHT_ON

    send_universe()


# ---------------- PRINTER CONFIG ----------------

USB_PRINTER = Usb(0x154F, 0x154F, interface=0)
NET_PRINTER = Network("192.168.1.251", 9100)


def reset_normal(p):
    p.hw("INIT")
    p.set(font="a", width=1, height=1, bold=False,
          underline=False, invert=False)
    p._raw(b'\x1b \x00')


def print_block(printer, title, text):
    reset_normal(printer)
    printer.text(f"{title.upper()}\n")
    printer.text("-" * 32 + "\n")
    printer.text(text.strip() + "\n\n")


# ---------------- STATE ----------------

running = False
response_received = False
stored_payload = None
stored_prompt = None


# ---------------- MODELS ----------------

class StartPayload(BaseModel):
    prompt: str


class DebatePayload(BaseModel):
    proposal: str
    conversation: list
    responses: dict
    votes: dict
    decision: str


# ---------------- PERFORMANCE THREAD ----------------

def performance_loop():
    global running, response_received

    running = True
    response_received = False

    # ---- PRINT PROMPT FIRST ----
    if stored_prompt:
        print("[PRINT] Printing proposal")
        for printer in [USB_PRINTER, NET_PRINTER]:
            try:
                print_block(printer, "PROPOSAL", stored_prompt)
            except Exception as e:
                print(f"[PRINT ERROR] {printer}: {e}")

    time.sleep(1)

    # ---- RESET DMX ----
    all_off()
    time.sleep(1)

    # ---- SYNC PHASE ----
    all_on()

    start_time = time.time()
    while time.time() - start_time < MIN_SYNC_TIME or not response_received:
        time.sleep(0.5)

    print("[SEQUENCE] Starting performance")

    all_off()
    time.sleep(1)

    # ---- AGENT PERFORMANCE ----
    for ch in CHANNELS:
        agent = CHANNEL_AGENT_MAP[ch]
        light_channel = CHANNEL_LIGHT_MAP[ch]

        print(f"[MOTOR] Channel {ch} ({agent}) ON")

        # Turn motor + corresponding light ON
        dmx_data[ch - 1] = MOTOR_ON
        dmx_data[light_channel - 1] = LIGHT_ON
        send_universe()

        time.sleep(CHARACTER_TIME)

        if stored_payload and agent in stored_payload.responses:
            response_text = stored_payload.responses[agent]
            for printer in [USB_PRINTER, NET_PRINTER]:
                try:
                    print_block(printer, agent, response_text)
                except Exception as e:
                    print(f"[PRINT ERROR] {printer}: {e}")

        # Turn motor + corresponding light OFF
        dmx_data[ch - 1] = MOTOR_OFF
        dmx_data[light_channel - 1] = LIGHT_OFF
        send_universe()

        time.sleep(PAUSE_TIME)

    all_off()

    # ---- PRINT VOTES + DECISION ----
    if stored_payload:
        print("[PRINT] Printing votes + decision")

        votes = stored_payload.votes
        decision = stored_payload.decision

        vote_text = (
            f"YES: {votes.get('YES', 0)}\n"
            f"NO: {votes.get('NO', 0)}\n\n"
            f"FINAL DECISION:\n{decision}"
        )

        for printer in [USB_PRINTER, NET_PRINTER]:
            try:
                print_block(printer, "VOTE RESULT", vote_text)
            except Exception as e:
                print(f"[PRINT ERROR] {printer}: {e}")

    print("[END] Performance complete")

    # ---- FINAL CUT (USB ONLY) ----
    try:
        USB_PRINTER.cut()
    except Exception as e:
        print(f"[CUT ERROR] {e}")

    running = False


# ---------------- API ----------------

@app.post("/start")
def start(payload: StartPayload):
    global running, stored_prompt

    if running:
        return {"status": "already running"}

    stored_prompt = payload.prompt

    threading.Thread(target=performance_loop, daemon=True).start()
    return {"status": "started"}


@app.post("/add_response")
def add_response(payload: DebatePayload):
    global response_received, stored_payload

    response_received = True
    stored_payload = payload

    print("[RESPONSE] Debate payload received")
    return {"status": "response received"}


@app.get("/is_running")
def is_running():
    return {"running": running}
