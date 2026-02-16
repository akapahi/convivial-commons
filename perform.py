from fastapi import FastAPI
from pydantic import BaseModel
import socket
import struct

# ---------------- CONFIG ----------------

ARTNET_PORT = 6454
UNIVERSE = 0

MOTOR_CHANNELS = [1, 2, 3, 4, 5]
LIGHT_CHANNELS = [10, 20, 30, 40, 50]

MOTOR_ON = 21
LIGHT_ON = 255

# ---------------- APP ----------------

app = FastAPI()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# ---------------- DMX ----------------

def send_dmx(frame):
    packet = b'Art-Net\x00'
    packet += struct.pack('<H', 0x5000)
    packet += struct.pack('>H', 14)
    packet += struct.pack('B', 0)
    packet += struct.pack('B', 0)
    packet += struct.pack('<H', UNIVERSE)
    packet += struct.pack('>H', len(frame))
    packet += bytes(frame)

    sock.sendto(packet, ("255.255.255.255", ARTNET_PORT))


def create_blank_frame():
    return [0] * 512


def blackout():
    send_dmx(create_blank_frame())


def activate(index):
    frame = create_blank_frame()

    motor_ch = MOTOR_CHANNELS[index - 1]
    light_ch = LIGHT_CHANNELS[index - 1]

    frame[motor_ch - 1] = MOTOR_ON
    frame[light_ch - 1] = LIGHT_ON

    send_dmx(frame)


def all_on():
    frame = create_blank_frame()

    for ch in MOTOR_CHANNELS:
        frame[ch - 1] = MOTOR_ON

    for ch in LIGHT_CHANNELS:
        frame[ch - 1] = LIGHT_ON

    send_dmx(frame)


# ---------------- API ----------------

class ChannelRequest(BaseModel):
    number: int


@app.post("/trigger")
def trigger_channel(data: ChannelRequest):
    number = data.number

    if number == 0:
        blackout()
        return {"status": "all_off"}

    if 1 <= number <= 5:
        activate(number)
        return {
            "status": "activated",
            "motor_channel": MOTOR_CHANNELS[number - 1],
            "light_channel": LIGHT_CHANNELS[number - 1]
        }

    if number == 6:
        all_on()
        return {"status": "all_on"}

    return {"error": "Send 0-6 only"}
