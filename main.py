import network
import time
import machine
import urequests as requests
import TM1637

# ---------- CONFIG ----------
WIFI_SSID = ""   
WIFI_PASS = ""   

BLYNK_TOKEN = "" 
BLYNK_API   = "http://blynk.cloud/external/api"

IR_PIN      = 13   
SERVO_PIN   = 18   
TM_CLK_PIN  = 22   
TM_DIO_PIN  = 21

OPEN_ANGLE   = 90
CLOSED_ANGLE = 0
OPEN_TIME    = 3 

V_IR_STATUS = "V0"
V_SLIDER    = "V1"
V_COUNT     = "V2"
V_MANUAL    = "V3"

# ---------- HARDWARE ----------
ir = machine.Pin(IR_PIN, machine.Pin.IN)
servo = machine.PWM(machine.Pin(SERVO_PIN), freq=50)
tm = TM1637.TM1637(clk=machine.Pin(TM_CLK_PIN), dio=machine.Pin(TM_DIO_PIN))
tm.brightness(7)

def set_servo_angle(angle):
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
        try:
            wifi.disconnect()
        except OSError:
            pass
        wifi.connect(WIFI_SSID, WIFI_PASS)
        print("Connecting to WiFi:", WIFI_SSID)

        for _ in range(20):          
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
def blynk_read(pin):
    try:
        r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&{pin}")
        value = str(r.text).strip('[]"{} \n')
        r.close()
        return value
    except Exception as e:
        print("Blynk read error:", e)
        return None

def blynk_read_int(pin, default):
    value = blynk_read(pin)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

def blynk_write(pin, value):
    value = str(value).replace(" ", "%20")
    try:
        r = requests.get(f"{BLYNK_API}/update?token={BLYNK_TOKEN}&{pin}={value}")
        r.close()
    except Exception as e:
        print("Blynk write error:", e)

# ---------- MAIN ----------
print("Running Task 5 - Manual override mode...")

count = 0
manual_mode = False
current_angle = CLOSED_ANGLE

tm.number(count)
blynk_write(V_COUNT, count)
blynk_write(V_IR_STATUS, "Not Detected")
set_servo_angle(current_angle)

while True:
    # Read the override switch
    new_manual = blynk_read_int(V_MANUAL, 1 if manual_mode else 0) == 1
    if new_manual != manual_mode:
        manual_mode = new_manual
        if manual_mode:
            print("MANUAL mode - IR sensor ignored")
            blynk_write(V_IR_STATUS, "Manual Mode")
        else:
            print("AUTO mode - IR sensor active")
            current_angle = CLOSED_ANGLE
            set_servo_angle(current_angle)
            blynk_write(V_IR_STATUS, "Not Detected")

    if manual_mode:
        # IR is ignored; servo follows the Blynk slider
        angle = blynk_read_int(V_SLIDER, current_angle)
        if angle != current_angle:
            current_angle = angle
            set_servo_angle(current_angle)
            print("Manual servo angle:", current_angle)

    elif ir.value() == 0:
        # Automatic IR -> servo action + counter
        count += 1
        print("Object detected! Count =", count)

        tm.number(count % 10000)
        blynk_write(V_COUNT, count)
        blynk_write(V_IR_STATUS, "Detected")

        set_servo_angle(OPEN_ANGLE)
        time.sleep(OPEN_TIME)
        set_servo_angle(CLOSED_ANGLE)
        current_angle = CLOSED_ANGLE
        blynk_write(V_IR_STATUS, "Not Detected")

        while ir.value() == 0:
            time.sleep(0.1)

    time.sleep(0.2)
