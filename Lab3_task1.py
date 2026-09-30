import network
import time
import machine
import urequests as requests

# ---------- CONFIG ----------
WIFI_SSID = ""   # <-- your WiFi name (2.4 GHz only)
WIFI_PASS = ""   # <-- your WiFi password

BLYNK_TOKEN = ""  # <-- your Blynk device auth token
BLYNK_API   = "http://blynk.cloud/external/api"

IR_PIN = 13

# ---------- HARDWARE ----------
ir = machine.Pin(IR_PIN, machine.Pin.IN)

# ---------- WIFI ----------
wifi = network.WLAN(network.STA_IF)

def connect_wifi():
    wifi.active(True)
    if wifi.isconnected():
        print("WiFi already connected!", wifi.ifconfig()[0])
        return

    while True:
        # Clear any half-finished connection left over from the last run
        try:
            wifi.disconnect()
        except OSError:
            pass
        wifi.connect(WIFI_SSID, WIFI_PASS)
        print("Connecting to WiFi:", WIFI_SSID)

        for _ in range(20):          # wait up to 20 seconds
            if wifi.isconnected():
                print("WiFi connected!", wifi.ifconfig()[0])
                return
            time.sleep(1)

        status = wifi.status()
        if status == getattr(network, "STAT_NO_AP_FOUND", -1):
            print("WiFi not found. Check the name and use a 2.4 GHz network (ESP32 cannot use 5 GHz).")
        elif status == getattr(network, "STAT_WRONG_PASSWORD", -1):
            print("Wrong WiFi password.")
        else:
            print("WiFi connection failed (status", status, "). Retrying...")

connect_wifi()

# ---------- BLYNK ----------
def blynk_write(pin, value):
    value = str(value).replace(" ", "%20")
    try:
        r = requests.get(f"{BLYNK_API}/update?token={BLYNK_TOKEN}&{pin}={value}")
        r.close()
    except Exception as e:
        print("Blynk write error:", e)

# ---------- MAIN ----------
print("Running Task 1 - IR sensor reading...")

last_status = None

while True:
    detected = ir.value() == 0
    status = "Detected" if detected else "Not Detected"

    if status != last_status:
        print("IR:", status)
        blynk_write("V0", status)
        last_status = status

    time.sleep(0.2)
