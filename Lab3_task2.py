import network
import time
import machine
import urequests as requests

# ---------- CONFIG ----------
WIFI_SSID = ""   # <-- your WiFi name (2.4 GHz only)
WIFI_PASS = ""   # <-- your WiFi password

BLYNK_TOKEN = ""  # <-- your Blynk device auth token
BLYNK_API   = "http://blynk.cloud/external/api"

SERVO_PIN = 18  

# ---------- HARDWARE ----------
servo = machine.PWM(machine.Pin(SERVO_PIN), freq=50)

def set_servo_angle(angle):
    # 50 Hz -> 20 ms period. 0.5 ms = 0 deg, 2.5 ms = 180 deg
    angle = max(0, min(180, int(angle)))
    pulse_us = 500 + (angle * 2000) // 180
    servo.duty_u16(pulse_us * 65535 // 20000)

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
def blynk_read(pin):
    try:
        r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&{pin}")
        value = str(r.text).strip('[]"{} \n')
        r.close()
        return value
    except Exception as e:
        print("Blynk read error:", e)
        return None

# ---------- MAIN ----------
print("Running Task 2 - Servo control via Blynk slider...")

current_angle = 0
set_servo_angle(current_angle)

while True:
    value = blynk_read("V1")

    if value is not None:
        try:
            angle = int(float(value))
            if angle != current_angle:
                set_servo_angle(angle)
                current_angle = angle
                print("Servo angle:", angle)
        except ValueError:
            pass

    time.sleep(0.2)
