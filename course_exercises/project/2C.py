import time
import wiringpi
import numpy
import spidev
import threading
from ClassLCD import LCD
import paho.mqtt.client as mqtt
from smbus2 import SMBus, i2c_msg
from bmp280 import BMP280
import requests

# Initialize I2C Bus
bus = SMBus(0)
address_lightsensor = 0x23  # i2c address
address_tempsensor = 0x77
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address_tempsensor)

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "channels/2829713/publish"
MQTT_CLIENT_ID = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_USER = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_PWD = "+cm5H5ON/XwqDbHqx0puzrUG"

# ThingSpeak Read API Key
THINGSPEAK_READ_API_KEY = "YIXOJPJHAAWBHM5S"
THINGSPEAK_CHANNEL_ID = "2829713"

# Pin Definitions
pin_switch0 = 3
pin_switch1 = 4
pin_switch_change = 12  # Mode toggle button
pin_CS_lcd = 15
pin_A = 2  # Stepper motor pins
pin_B = 5
pin_C = 7
pin_D = 8

# Setup WiringPi
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin_switch0, 0)
wiringpi.pinMode(pin_switch1, 0)
wiringpi.pinMode(pin_switch_change, 0)
wiringpi.pinMode(pin_CS_lcd, 1)
wiringpi.pinMode(pin_A, 1)
wiringpi.pinMode(pin_B, 1)
wiringpi.pinMode(pin_C, 1)
wiringpi.pinMode(pin_D, 1)

# LCD Functions
def ActivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 0)
    time.sleep(0.000005)

def DeactivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 1)
    time.sleep(0.000005)

ActivateLCD()
lcd_1 = LCD({'SCLK': 14, 'DIN': 11, 'DC': 9, 'CS': 15, 'RST': 10, 'LED': 6})
lcd_1.set_backlight(1)

# Stepper Motor Functions
def perform_step(step_sequence):
    wiringpi.digitalWrite(pin_A, step_sequence[0])
    wiringpi.digitalWrite(pin_B, step_sequence[1])
    wiringpi.digitalWrite(pin_C, step_sequence[2])
    wiringpi.digitalWrite(pin_D, step_sequence[3])

def rotate_motor(steps, direction=1):
    full_step_sequence = [
        [1, 0, 0, 1],
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 1],
    ]
    for _ in range(steps):
        for step in (full_step_sequence if direction == 1 else reversed(full_step_sequence)):
            perform_step(step)
            time.sleep(0.01)

# MQTT Setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()

# Mode Toggle
adjusting_brightness = True
def toggle_mode():
    global adjusting_brightness
    adjusting_brightness = not adjusting_brightness
    mode = "Brightness" if adjusting_brightness else "Temperature"
    print(f"Mode switched to: {mode}")

# Functions to read sensors
def get_lux():
    write = i2c_msg.write(address_lightsensor, [0x10])
    read = i2c_msg.read(address_lightsensor, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return (((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2

def get_temperature():
    return bmp280.get_temperature()

def read_thingspeak(field):
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/{field}.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                return float(feeds[-1].get(f"field{field}", 0))
    except Exception as e:
        print(f"Failed to read from ThingSpeak: {e}")
    return 0

desired_light = read_thingspeak(3)
desired_temp = read_thingspeak(4)

screens_state = 'closed'

# Main Loop
try:
    print("Start")
    while True:
        if wiringpi.digitalRead(pin_switch_change) == 0:
            time.sleep(0.1)
            toggle_mode()

        if wiringpi.digitalRead(pin_switch0) == 0:
            time.sleep(0.1)
            if adjusting_brightness:
                desired_light = min(desired_light + 10, 100)
            else:
                desired_temp = min(desired_temp + 0.5, 50)

        if wiringpi.digitalRead(pin_switch1) == 0:
            time.sleep(0.1)
            if adjusting_brightness:
                desired_light = max(desired_light - 10, 0)
            else:
                desired_temp = max(desired_temp - 0.5, 0)

        lux_value = round(max(0, get_lux()))
        temp_value = get_temperature()

        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Lux:{lux_value}')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f'Temp:{temp_value:.1f}C')
        lcd_1.refresh()
        DeactivateLCD()

        if desired_light > 200 and screens_state == 'open':
            lcd_1.put_string(f'\n--> closing')
            print('Closing screens')
            rotate_motor(100, direction=1)
            screens_state = 'closed'  # Update state
        elif desired_light < 100 and screens_state == 'closed':
            lcd_1.put_string(f'\n--> opening')
            print('Opening screens')
            rotate_motor(100, direction=-1)
            screens_state = 'open'  # Update state

        client.publish(MQTT_TOPIC, f"field1={lux_value}&field2={temp_value:.1f}&field3={desired_light}&field4={desired_temp}")
        time.sleep(15)

except KeyboardInterrupt:
    ActivateLCD()
    lcd_1.clear()
    lcd_1.refresh()
    lcd_1.set_backlight(0)
    DeactivateLCD()
    print("Shutdown complete.")
