# final.py

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
MQTT_TOPIC = "channels/2829713/publish"
MQTT_CLIENT_ID = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_USER = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_PWD = "+cm5H5ON/XwqDbHqx0puzrUG"

# ThingSpeak Read API Key
THINGSPEAK_READ_API_KEY = "YIXOJPJHAAWBHM5S"
THINGSPEAK_CHANNEL_ID = "2829713"

# Callback functions (reaction to events during operation)
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected OK with result code " + str(rc))
    else:
        print("Bad connection with result code " + str(rc))

def on_disconnect(client, userdata, flags, rc=0):
    print("Disconnected result code " + str(rc))

# MQTT Setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()  # Start the loop

# Initialize I2C Bus
bus = SMBus(0)
address_lightsensor = 0x23  # i2c address
address_tempsensor = 0x77
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address_tempsensor)

# Pin initialisation
pin_switch_change = 12
pin_switch0 = 3
pin_switch1 = 4
pinTrg = 16
pinEcho = 13
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
wiringpi.pinMode(pin_switch_change, 0)
wiringpi.pinMode(pin_switch0, 0)                  # Set pins as input
wiringpi.pinMode(pin_switch1, 0)
wiringpi.pinMode(pinTrg, 1)                       # Set pin to mode 1 (OUTPUT)
wiringpi.pinMode(pinEcho, 0)                      # Set pin to mode 0 (INPUT)
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
# BH1750
def get_lux(bus, address_lightsensor):
    write = i2c_msg.write(address_lightsensor, [0x10])  # 1lx resolution 120ms see datasheet
    read = i2c_msg.read(address_lightsensor, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return (((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2  # Conversion

# BMP280
def get_temperature():
    return bmp280.get_temperature()

# Hysteresis Variables
last_brightness = -1  # Initialize with an impossible value
hysteresis = 5  # Minimum change required to update

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

brightness = read_thingspeak(1)
room_temp = read_thingspeak(2)
room_lights = read_thingspeak(3)
desired_temp = read_thingspeak(4)

# Other variables
threshold = 200
adjusting_room_lights = True # Start in lights adjustment mode
debounce_time = 0.5  # Reduced debounce time for quicker button response
screens_state = 'closed'
bright_notified = False
cold_notified = False
pi_logo = [
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0x7f, 0xff, 0xff, 0xff, 0x7f, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0xfe, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xf9, 0xe3, 0xc7, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xcf, 0xc7, 0xe0, 0xf0, 0xff, 0xff, 0xff, 0xf0, 0xe0, 0xc3, 0xc7, 0xcf, 0xcf, 0xcf, 0xc7, 0xe3, 0xf0, 0xe3, 0xc7, 0xcf, 0xcf, 0xcf, 0xc7, 0xc3, 0xe0, 0xf0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x03, 0xf7, 0xfb, 0xfb, 0xf7, 0xff, 0x07, 0xfb, 0xfb, 0xfb, 0x07, 0xff, 0x07, 0xfb, 0xfb, 0xfb, 0x07, 0xff, 0x03, 0xfb, 0xe7, 0xfb, 0x07, 0xff, 0x07, 0xfb, 0xfb, 0xfb, 0x77, 0xff, 0x07, 0xfb, 0xfb, 0xfb, 0x07, 0xff, 0x03, 0xf7, 0xfb, 0xfb, 0xfb, 0x07, 0xff, 0x00, 0xfb, 0xfb, 0xfb, 0x7f, 0xff, 0x03, 0xf7, 0xfb, 0xfb, 0xf7, 0xff, 0x07, 0xfb, 0xfb, 0xfb, 0x07, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0x07, 0xdb, 0xdb, 0xdb, 0x67, 0xff, 0x03, 0xf7, 0xfb, 0xfb, 0xf7, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xfe, 0xff, 0xfe, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xff, 0xff, 0xff, 0xff, 0xff
]

# Flag to control the thread execution
running = True  

def toggle_mode():
    global adjusting_room_lights
    adjusting_room_lights = not adjusting_room_lights
    mode = "Room lights" if adjusting_room_lights else "Room temperature"
    print("----------------------------")
    print(f"Mode switched to: {mode}")
last_mode_switch_time = 0  # To debounce mode switch

def handle_switches():
    global adjusting_room_lights, room_lights, desired_temp, last_mode_switch_time
    while running:
        current_time = time.time()

        # Detect mode switch button press
        if wiringpi.digitalRead(pin_switch_change) == 0:  # Active low
            if current_time - last_mode_switch_time > debounce_time:  # Simple debounce
                toggle_mode()
                last_mode_switch_time = current_time
            time.sleep(debounce_time)  # Debounce delay

        # Check if buttons are pressed (button reactions happen immediately)
        if wiringpi.digitalRead(pin_switch0) == 0:  # input is active low
            time.sleep(debounce_time)  # Anti bouncing
            if adjusting_room_lights:
                room_lights = int(numpy.clip(room_lights + 10, 0, 100))
                print("----------------------------")
                print(f'lights changed to: {room_lights} %')
            else:
                desired_temp = float(numpy.clip(desired_temp + 0.5, 0, 50))
                print("----------------------------")
                print(f'temperature changed to: {desired_temp} °C')

        if wiringpi.digitalRead(pin_switch1) == 0:  # input is active low
            time.sleep(debounce_time)  # Anti bouncing
            if adjusting_room_lights:
                room_lights = int(numpy.clip(room_lights - 10, 0, 100))
                print("----------------------------")
                print(f'lights changed to: {room_lights} %')
            else:
                desired_temp = float(numpy.clip(desired_temp - 0.5, 0, 50))
                print("----------------------------")
                print(f'temperature changed to: {desired_temp:.1f} °C')

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
    print('start')
    while True:
        # get sensor values at start of every loop
        sens_brightness_value = get_lux(bus, address_lightsensor)
        sens_brightness_value = round(max(0, sens_brightness_value))  # Ensure no negative values
        sens_temperature_value = bmp280.get_temperature()

        # Hysteresis Check
        if last_brightness == -1 or abs(sens_brightness_value - last_brightness) > hysteresis:
            last_brightness = sens_brightness_value  # Update stored value

        # distance measuring for adjusting room lights
        wiringpi.digitalWrite(pinTrg, 1)              # output high
        time.sleep(0.00001)
        wiringpi.digitalWrite(pinTrg, 0)              # output low
        while wiringpi.digitalRead(pinEcho) == 0:       
            pass
        signal_high = time.time()                   # note the start time of first echo
        while wiringpi.digitalRead(pinEcho) == 1:
            pass
        signal_low = time.time()                    # note the end time of last echo
        time_passed = signal_low - signal_high
        distance = time_passed * 17000
        print("----------------------------")
        print('Measured Distance =', round(distance, 1), 'cm')

        # If distance is less than 20 cm, set room lights to 10%
        if distance < 20:
            room_lights = 10
            print("----------------------------")
            print(f'Good night, dimming lights to {room_lights} %')

        MQTT_DATA = f"field1={sens_brightness_value}&field2={sens_temperature_value:.1f}&field3={room_lights}&field4={desired_temp:.1f}"
        try:
            client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        except OSError:
            client.reconnect()

        brightness = read_thingspeak(1)
        room_temp = read_thingspeak(2)

        print("----------------------------")
        print(f'Brightness: {brightness:.0f} lux')
        print(f'Room lights: {room_lights:.0f} %')
        print(f'Room temp: {room_temp:.1f} °C')
        print(f'Desired temp: {desired_temp:.1f} °C')

        # Display values on LCD
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'B: {brightness:.0f} lux')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f'L: {room_lights:.0f} %')
        lcd_1.go_to_xy(0, 20)
        lcd_1.put_string(f'T: {room_temp:.1f} °C')
        lcd_1.go_to_xy(0, 30)
        lcd_1.put_string(f'D: {desired_temp:.1f} °C')

        # Motor control logic ONLY based on ThingSpeak brightness
        if brightness > threshold and screens_state == 'open':
            lcd_1.go_to_xy(0, 40)
            lcd_1.put_string(f'--> closing')
            print("--------------------")
            print('Closing screens')
            rotate_motor_threaded(100)  # Use threaded version
            screens_state = 'closed'  # Update state
        elif brightness <= threshold and screens_state == 'closed':
            lcd_1.go_to_xy(0, 40)
            lcd_1.put_string(f'--> opening')
            print("--------------------")
            print('Opening screens')
            rotate_motor_reversed_threaded(100)  # Use threaded version
            screens_state = 'open'  # Update state

        lcd_1.refresh()
        DeactivateLCD()    

        # PushOver message to phone
        if brightness > threshold:
            if not bright_notified:  # Send only if not already sent
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Closed screens to avoid high room temp",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
                bright_notified = True  # Mark as notified
        else:
            bright_notified = False # Reset if condition no longer holds

        """ if room_temp < 18:
            if not cold_notified:  # Send only if not already sent
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Cold",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
                cold_notified = True  # Mark as notified
        else:
            cold_notified = False  # Reset if condition no longer holds """

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