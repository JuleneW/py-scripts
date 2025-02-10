# final_group.py

import time
import wiringpi
import sys
import numpy
import spidev
from ClassLCD import LCD
import paho.mqtt.client as mqtt
from smbus2 import SMBus, i2c_msg
from bmp280 import BMP280
import requests
import threading
import http.client, urllib # for PushOver messages

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC_WAARDES = "channels/2792379/publish"
MQTT_TOPIC_GEWENST = "channels/2792381/publish"
MQTT_CLIENT_ID = "MS4nJTksJgwXHywIAhUUOxs"
MQTT_USER = "MS4nJTksJgwXHywIAhUUOxs"
MQTT_PWD = "rywz2S3vL/h5WswSrmMmIoNM"

# ThingSpeak Read API Key
THINGSPEAK_READ_API_KEY_WAARDES = "0OOB9HY94B6XQ63M"
THINGSPEAK_CHANNEL_ID_WAARDES = "2792379"
THINGSPEAK_READ_API_KEY_GEWENST = "94U2IKT6YRPREMPN"
THINGSPEAK_CHANNEL_ID_GEWENST = "2792381"

# Callback functions (reaction to events during operation)
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        pass
        #print("Connected OK with result code " + str(rc))
    else:
        print("Bad connection with result code " + str(rc))
def on_disconnect(client, userdata, flags, rc=0):
    #print("Disconnected result code " + str(rc))
    pass

# MQTT Setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()  # Start the loop

# Initialize I2C Bus
bus = SMBus(0)
address_tempsensor = 0x77
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address_tempsensor)

# Pin initialisation
pin_switch0 = 3
pin_switch1 = 4
# LCD pins
PIN_OUT = {
    'SCLK': 14,
    'DIN': 11,
    'DC': 9,
    'CS': 15,
    'RST': 10,
    'LED': 6,  # backlight
}
pin_CS_lcd = 15
# stepper motor pins
pin_A = 2 # gpio pin for coil A
pin_B = 5 # gpio pin for coil B
pin_C = 7 # gpio pin for coil C
pin_D = 8 # gpio pin for coil D

# Stepper motor sequence for full step
full_step_sequence = [
    [1, 0, 0, 1, 1, 0, 0, 1],  # Step 1: Coil A
    [1, 1, 0, 0, 1, 1, 0, 0],  # Step 2: Coil B
    [0, 1, 1, 0, 0, 1, 1, 0],  # Step 3: Coil C
    [0, 0, 1, 1, 0, 0, 1, 1],  # Step 4: Coil D
]

# Pin setup
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin_switch0, 0)                  # Set pins as input
wiringpi.pinMode(pin_switch1, 0)
wiringpi.pinMode(pin_A, 1)                  # gpio pin for coil A
wiringpi.pinMode(pin_B, 1)                  # gpio pin for coil B
wiringpi.pinMode(pin_C, 1)                  # gpio pin for coil C
wiringpi.pinMode(pin_D, 1)                  # gpio pin for coil D
wiringpi.pinMode(pin_CS_lcd, 1)  # Set pin to mode 1 (OUTPUT)

# Function to perform a single step
def perform_step(step_sequence):
    wiringpi.digitalWrite(pin_A, step_sequence[0])
    wiringpi.digitalWrite(pin_B, step_sequence[1])
    wiringpi.digitalWrite(pin_C, step_sequence[2])
    wiringpi.digitalWrite(pin_D, step_sequence[3])

def rotate_motor_threaded(number_steps):
    def motor_task():
        for i in range(number_steps):
            for step in full_step_sequence:
                perform_step(step)
                time.sleep(0.01)  # Step delay

    # Start motor in a new thread
    motor_thread = threading.Thread(target=motor_task)
    motor_thread.start()

def rotate_motor_reversed_threaded(number_steps):
    def motor_task():
        for i in range(number_steps - 1, -1, -1):
            for step in full_step_sequence:
                perform_step(step)
                time.sleep(0.01)  # Step delay

    # Start motor in a new thread
    motor_thread = threading.Thread(target=motor_task)
    motor_thread.start()

# get sensor values
# BMP280
def get_temperature():
    return bmp280.get_temperature()

def read_thingspeak_WAARDES():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID_WAARDES}/fields/5.json?api_key={THINGSPEAK_READ_API_KEY_WAARDES}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                return float(feeds[-1].get(f"field5", 0))
    except Exception as e:
        print(f"Failed to read from ThingSpeak: {e}")
    return 0

def read_thingspeak_GEWENST():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID_GEWENST}/fields/5.json?api_key={THINGSPEAK_READ_API_KEY_GEWENST}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                return float(feeds[-1].get(f"field5", 0))
    except Exception as e:
        print(f"Failed to read from ThingSpeak: {e}")
    return 0

# Other variables
threshold = 22
debounce_time = 0.5  # Reduced debounce time for quicker button response
screens_state = 'open'
hot_notified = False
# Flag to control the thread execution
running = True  
pi_logo = [
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0xff, 0xff, 0xff, 0x7f, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xf9, 0xe3, 0xc7, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xc7, 0xe0, 0xf0, 0xff, 0xff, 0xff, 0xf0, 0xe0, 0xc3, 0xc7, 0xcf, 0xcf, 0xcf, 0xc7, 0xe3, 0xf0, 0xe3, 0xc7, 0xcf, 0xcf, 0xcf, 0xc7, 0xc3, 0xe0, 0xf0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xfd, 0xfe, 0xfe, 0xfe, 0xfd, 0xff, 0x81, 0x7e, 0x7e, 0x7e, 0x7e, 0x81, 0xff, 0x81, 0x7e, 0x7e, 0x7e, 0x7e, 0x81, 0xff, 0x00, 0xfe, 0xfe, 0x01, 0xfe, 0xfe, 0x01, 0xff, 0xff, 0xff, 0x70, 0x76, 0x76, 0x76, 0x76, 0x8e, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff
    ]

def handle_switches():
    global desired_room_temp
    while running:
        current_time = time.time()
        # Check if buttons are pressed (button reactions happen immediately)
        if wiringpi.digitalRead(pin_switch0) == 0:  # input is active low
            time.sleep(debounce_time)  # Anti bouncing
            desired_room_temp = float(numpy.clip(desired_room_temp + 0.5, 0, 50))
            print(f'Change temperature to: {desired_room_temp:.1f} °C')

            # Publish updated value to ThingSpeak
            MQTT_DATA_GEWENST = f"field5={desired_room_temp:.1f}"
            client.publish(topic=MQTT_TOPIC_GEWENST, payload=MQTT_DATA_GEWENST, qos=0, retain=False)

        if wiringpi.digitalRead(pin_switch1) == 0:  # input is active low
            time.sleep(debounce_time)  # Anti bouncing
            desired_room_temp = float(numpy.clip(desired_room_temp - 0.5, 0, 50))
            print(f'Change temperature to: {desired_room_temp:.1f} °C')

            # Publish updated value to ThingSpeak
            MQTT_DATA_GEWENST = f"field5={desired_room_temp:.1f}"
            client.publish(topic=MQTT_TOPIC_GEWENST, payload=MQTT_DATA_GEWENST, qos=0, retain=False)

        time.sleep(0.05)  # Short sleep to avoid CPU overload

# Start the switch-handling thread
switch_thread = threading.Thread(target=handle_switches, daemon=True)
switch_thread.start()

# LCD functions
def ActivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 0)
    time.sleep(0.000005)
def DeactivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 1)
    time.sleep(0.000005)

# Initialize and activate LCD before anything else
ActivateLCD()
lcd_1 = LCD(PIN_OUT)
lcd_1.set_backlight(1)
LCD.draw_image(lcd_1, pi_logo, 84, 48, x = 0, y = 0)
lcd_1.refresh()
time.sleep(2)  # Allow time to read the initial message
lcd_1.clear()
lcd_1.refresh()

# Main loop
try:
    sens_temperature_value = bmp280.get_temperature()
    print('start')
    while True:
        # get sensor values at start of every loop
        sens_temperature_value = bmp280.get_temperature()

        MQTT_DATA_WAARDES = f"field5={sens_temperature_value:.1f}"
        try:
            client.publish(topic=MQTT_TOPIC_WAARDES, payload=MQTT_DATA_WAARDES, qos=0, retain=False)
        except OSError:
            client.reconnect()

        room_temp = read_thingspeak_WAARDES()
        desired_room_temp = read_thingspeak_GEWENST()

        print("--------------------")
        print(f'Room temp: {room_temp:.1f} °C')
        print(f'Desired room temp: {desired_room_temp:.1f} °C')
        print("--------------------")

        # Display values on LCD
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Thermostat')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f'Temp: {room_temp:.1f} °C')
        lcd_1.go_to_xy(0, 20)
        lcd_1.put_string(f'--> {desired_room_temp:.1f} °C')

        # Motor control logic ONLY based on ThingSpeak brightness
        if room_temp > threshold and screens_state == 'open':
            lcd_1.go_to_xy(0, 40)
            lcd_1.put_string(f'--> closing')
            print("--------------------")
            print('Closing screens')
            rotate_motor_threaded(100)  # Use threaded version
            screens_state = 'closed'  # Update state
        elif room_temp <= threshold and screens_state == 'closed':
            lcd_1.go_to_xy(0, 40)
            lcd_1.put_string(f'--> opening')
            print("--------------------")
            print('Opening screens')
            rotate_motor_reversed_threaded(100)  # Use threaded version
            screens_state = 'open'  # Update state
        lcd_1.refresh()
        DeactivateLCD()    

        # PushOver message to phone
        if room_temp > 23:
            if not hot_notified:  # Send only if not already sent
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Room is hot",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
                hot_notified = True  # Mark as notified
        else:
            hot_notified = False # Reset if condition no longer holds
        time.sleep(15)
    
except KeyboardInterrupt:
    ActivateLCD()
    lcd_1.clear()
    lcd_1.refresh()
    lcd_1.set_backlight(0)
    DeactivateLCD()
    wiringpi.digitalWrite(pin_A, 0)
    wiringpi.digitalWrite(pin_B, 0)
    wiringpi.digitalWrite(pin_C, 0)
    wiringpi.digitalWrite(pin_D, 0)
    print("\nShutdown complete.")
    running = False  # Stop the thread
    switch_thread.join()  # Wait for thread to terminate cleanly