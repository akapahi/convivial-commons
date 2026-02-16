#include <PN532_HSU.h>
#include <PN532.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ---------------- WIFI ----------------
const char *ssid = "Internet";
const char *password = "password";

// ---------------- SERVER ----------------
const char *serverUrl = "http://covivial.local:8000/start_discussion";

// ---------------- NFC ----------------
PN532_HSU pn532hsu(Serial1);
PN532 nfc(pn532hsu);

// Track last UID to prevent repeat trigger
uint8_t lastUID[7];
uint8_t lastUIDLength = 0;
bool hasLastUID = false;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, 16, 17);

  pinMode(LED_BUILTIN, OUTPUT);

  // ---- WIFI CONNECT ----
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);

  uint8_t attempt = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    attempt++;
    if (attempt > 40) {
      Serial.println("\nWiFi failed. Restarting...");
      ESP.restart();
    }
  }

  digitalWrite(LED_BUILTIN, HIGH);

  Serial.println("\nWiFi connected!");
  Serial.println(WiFi.localIP());
  Serial.println("Ready to scan NFC tags...");

  // ---- NFC INIT ----
  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println("PN532 not found");
    while (1);
  }

  nfc.SAMConfig();
}

void loop() {

  uint8_t success;
  uint8_t uid[7];
  uint8_t uidLength;

  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength);

  if (success) {

    if (!hasLastUID || !compareUID(uid, lastUID, uidLength)) {

      memcpy(lastUID, uid, uidLength);
      lastUIDLength = uidLength;
      hasLastUID = true;

      Serial.println("Tag detected — reading NDEF...");

      String topic = readNDEFText();

      if (topic != "") {
        sendTopic(topic);
      } else {
        Serial.println("No valid text found.");
      }

      delay(1500); // debounce
    }
  }

  delay(200);
}

// ---------------- UID COMPARE ----------------
bool compareUID(uint8_t *uid1, uint8_t *uid2, uint8_t len) {
  if (len != lastUIDLength) return false;

  for (uint8_t i = 0; i < len; i++) {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

// ---------------- READ ULTRALIGHT ----------------
String readNDEFText() {

  uint8_t data[4];
  uint8_t buffer[64];
  int index = 0;

  // Read pages 4–15
  for (uint8_t page = 4; page < 16; page++) {

    if (!nfc.mifareultralight_ReadPage(page, data)) {
      Serial.print("Read failed at page ");
      Serial.println(page);
      return "";
    }

    for (int i = 0; i < 4; i++) {
      buffer[index++] = data[i];
    }
  }

  // Find NDEF Text record (0x54 = 'T')
  for (int i = 0; i < index; i++) {
    if (buffer[i] == 0x54) {  // 'T' record type

      uint8_t statusByte = buffer[i + 1];
      uint8_t languageLength = statusByte & 0x3F;

      int textStart = i + 2 + languageLength;

      String text = "";

      for (int j = textStart; j < index; j++) {
        if (isPrintable(buffer[j])) {
          text += (char)buffer[j];
        }
      }

      Serial.print("Clean extracted text: ");
      Serial.println(text);

      return text;
    }
  }

  Serial.println("No NDEF text record found.");
  return "";
}


// ---------------- SEND POST ----------------
void sendTopic(String topicId) {

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected.");
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  String jsonPayload = "{\"topic_id\":\"" + topicId + "\"}";

  Serial.println("Sending POST:");
  Serial.println(jsonPayload);

  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.print("Response code: ");
    Serial.println(httpResponseCode);
    Serial.println(http.getString());
  } else {
    Serial.print("POST failed: ");
    Serial.println(httpResponseCode);
  }

  http.end();
}
