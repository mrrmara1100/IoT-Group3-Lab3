import network
import time
import machine
import urequests as requests
import TM1637

# ---------- CONFIG ----------
WIFI_SSID = ""   # <-- your WiFi name (2.4 GHz only)
WIFI_PASS = ""   # <-- your WiFi password

BLYNK_TOKEN = ""  # <-- your Blynk device auth token
BLYNK_API   = "http://blynk.cloud/external/api"

IR_PIN      = 13   
SERVO_PIN   = 18   
TM_CLK_PIN  = 22   
TM_DIO_PIN  = 21   

OPEN_ANGLE   = 90
CLOSED_ANGLE = 0
OPEN_TIME    = 3

# Blynk virtual pins - change these to match your Blynk datastreams
V_IR_STATUS = "V0"   # String  -> Label widget
V_COUNT     = "V2"   # Integer -> Gauge widget

# ---------- HARDWARE ----------
ir = machine.Pin(IR_PIN, machine.Pin.IN)
servo = machine.PWM(machine.Pin(SERVO_PIN), freq=50)
tm = TM1637.TM1637(clk=machine.Pin(TM_CLK_PIN), dio=machine.Pin(TM_DIO_PIN))
tm.brightness(7)

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

tm.show("----")
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
print("Running Task 4 - IR counter + TM1637 + Blynk...")

count = 0
tm.number(count)
blynk_write(V_COUNT, count)
blynk_write(V_IR_STATUS, "Not Detected")
set_servo_angle(CLOSED_ANGLE)

while True:
    if ir.value() == 0:
        count += 1
        print("Object detected! Count =", count)

        # Update display and Blynk with the same value
        tm.number(count % 10000)  # TM1637 shows max 4 digits
        blynk_write(V_COUNT, count)
        blynk_write(V_IR_STATUS, "Detected")

        set_servo_angle(OPEN_ANGLE)
        time.sleep(OPEN_TIME)
        set_servo_angle(CLOSED_ANGLE)
        blynk_write(V_IR_STATUS, "Not Detected")

        # Wait until the object has left so one object = one count
        while ir.value() == 0:
            time.sleep(0.1)

    time.sleep(0.1)
