import network
import time
import machine
import urequests as requests

# ---------- CONFIG ----------
WIFI_SSID = ""   # <-- your WiFi name (2.4 GHz only)
WIFI_PASS = ""   # <-- your WiFi password

BLYNK_TOKEN = ""  # <-- your Blynk device auth token
BLYNK_API   = "http://blynk.cloud/external/api"

IR_PIN    = 13  
SERVO_PIN = 18 

OPEN_ANGLE   = 90   
CLOSED_ANGLE = 0    
OPEN_TIME    = 3    

# ---------- HARDWARE ----------
ir = machine.Pin(IR_PIN, machine.Pin.IN)
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
def blynk_write(pin, value):
    value = str(value).replace(" ", "%20")
    try:
        r = requests.get(f"{BLYNK_API}/update?token={BLYNK_TOKEN}&{pin}={value}")
        r.close()
    except Exception as e:
        print("Blynk write error:", e)

# ---------- MAIN ----------
print("Running Task 3 - Automatic IR -> Servo...")

set_servo_angle(CLOSED_ANGLE)
blynk_write("V0", "Not Detected")

while True:
    if ir.value() == 0:
        print("Object detected -> opening servo")
        blynk_write("V0", "Detected")
        set_servo_angle(OPEN_ANGLE)

        time.sleep(OPEN_TIME)

        print("Closing servo")
        set_servo_angle(CLOSED_ANGLE)
        blynk_write("V0", "Not Detected")

        # Wait until the object has left so one object = one trigger
        while ir.value() == 0:
            time.sleep(0.1)

    time.sleep(0.1)
