#include <WiFi.h>
#include <WiFiUdp.h>

const char* ssid = "Internet";
const char* password = "password";

WiFiUDP udp;
#define ARTNET_PORT 6454

// ===== PWM =====
#define PWM_PIN   15
#define PWM_FREQ  1000
#define PWM_RES   8   // 8-bit (0–255)

// ===== DMX =====
#define DMX_CHANNEL 2
#define START_THRESHOLD 20

uint8_t packetBuffer[600];

// ===== MOTOR PULSE LOGIC =====
bool motorRunning = false;

int dutyMin = 13;   // ~5%
int dutyMax = 80;   // ~30%

int duty = dutyMin;
int step = 1;

unsigned long lastUpdate = 0;
int pulseSpeed = 20;   // ms between steps

void setup() {
  Serial.begin(115200);

  // NEW ESP32 CORE v3 PWM SETUP
  ledcAttach(PWM_PIN, PWM_FREQ, PWM_RES);
  ledcWrite(PWM_PIN, 0);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());

  udp.begin(ARTNET_PORT);
  Serial.println("Listening Art-Net");
}

void loop() {

  // ===== RECEIVE ARTNET =====
  int packetSize = udp.parsePacket();
  if (packetSize) {
    udp.read(packetBuffer, 600);

    if (memcmp(packetBuffer, "Art-Net", 7) == 0) {

      int dmxStart = 18;
      int value = packetBuffer[dmxStart + DMX_CHANNEL - 1];

      if (value > START_THRESHOLD && !motorRunning) {
        motorRunning = true;
        duty = dutyMin;
        step = 1;
        Serial.println("MOTOR START");
      }

      if (value <= START_THRESHOLD && motorRunning) {
        motorRunning = false;
        ledcWrite(PWM_PIN, 0);
        Serial.println("MOTOR STOP");
      }
    }
  }

  if (motorRunning) {

    if (millis() - lastUpdate > pulseSpeed) {
      lastUpdate = millis();

      duty += step;

      if (duty >= dutyMax) step = -1;
      if (duty <= dutyMin) step = 1;

      ledcWrite(PWM_PIN, duty);
    }
  }
}
