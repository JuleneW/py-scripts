import time
import wiringpi
import OrangePi.GPIO as GPIO
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

BUTTON1_PIN = 3
BUTTON2_PIN = 4
GPIO.setmode(GPIO.BCM)  # or GPIO.BOARD depending on your setup
GPIO.setup(BUTTON1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
def button_listener():
    while True:
        if GPIO.input(BUTTON1_PIN) == GPIO.LOW:
            print("Button 1 Pressed!")
            # Publish MQTT message or trigger event
        if GPIO.input(BUTTON2_PIN) == GPIO.LOW:
            print("Button 2 Pressed!")
            # Publish MQTT message or trigger event
        time.sleep(0.1)  # Avoid excessive CPU usage
button_thread = threading.Thread(target=button_listener, daemon=True)
button_thread.start()

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

# Threshold in lux
THRESHOLD = 200

# Pin definitions
pin_switch_change = 12
pin_switch0 = 3
pin_switch1 = 4
debounce_time = 0.01  # Reduced debounce time for quicker button response
pinTrg = 16
pinEcho = 13
PIN_OUT = {
    'SCLK': 14,
    'DIN': 11,
    'DC': 9,
    'CS': 15,
    'RST': 10,
    'LED': 6,  # backlight
}
# stepper motor pins
pin_A = 2 # gpio pin for coil A
pin_B = 5 # gpio pin for coil B
pin_C = 7 # gpio pin for coil C
pin_D = 8 # gpio pin for coil D
pin_CS_lcd = 15

# Stepper motor sequence for full step
full_step_sequence = [
    [1, 0, 0, 1, 1, 0, 0, 1],  # Step 1: Coil A
    [1, 1, 0, 0, 1, 1, 0, 0],  # Step 2: Coil B
    [0, 1, 1, 0, 0, 1, 1, 0],  # Step 3: Coil C
    [0, 0, 1, 1, 0, 0, 1, 1],  # Step 4: Coil D
]

# Setup WiringPi
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin_A, 1)
wiringpi.pinMode(pin_B, 1)
wiringpi.pinMode(pin_C, 1)
wiringpi.pinMode(pin_D, 1)
wiringpi.pinMode(pin_switch_change, 0)
wiringpi.pinMode(pin_switch0, 0)                  # Set pins as input
wiringpi.pinMode(pin_switch1, 0)
wiringpi.pinMode(pinTrg, 1)                       # Set pin to mode 1 (OUTPUT)
wiringpi.pinMode(pinEcho, 0)                      # Set pin to mode 0 (INPUT)
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
    motor_thread = threading.Thread(target=motor_task, daemon= True)
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

# Hysteresis Variables
last_brightness = -1  # Initialize with an impossible value
hysteresis_threshold = 5  # Minimum change required to update
default_value = 50

# Setup BH1750
bus.write_byte(address_lightsensor, 0x10)

def get_value(bus, address_lightsensor):
    write = i2c_msg.write(address_lightsensor, [0x10])  # 1lx resolution 120ms see datasheet
    read = i2c_msg.read(address_lightsensor, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return (((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2  # Conversion

# LCD functions
def ActivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 0)
    time.sleep(0.000005)

def DeactivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 1)
    time.sleep(0.000005)

def read_brightness():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/1.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                latest_entry = feeds[-1]  # Get the most recent data
                brightness_value = latest_entry.get("field1", default_value)
                if brightness_value is not None:
                    return int(float(brightness_value))  # Convert to int
        print("No valid brightness value found in ThingSpeak response")
    except Exception as e:
        print(f"Failed to read brightness from ThingSpeak: {e}")
    return default_value  # Default fallback

def read_temperature():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/2.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                latest_entry = feeds[-1]  # Get the most recent data
                temperature_value = latest_entry.get("field2", default_value)
                if temperature_value is not None:
                    return float(temperature_value)
        print("No valid temperature value found in ThingSpeak response")
    except Exception as e:
        print(f"Failed to read temperature from ThingSpeak: {e}")
    return default_value  # Default fallback

# Variables
default_lights = 50
default_temp = 20
adjusting_lights = True # Start in brightness adjustment mode
def toggle_mode():
    global adjusting_lights
    adjusting_lights = not adjusting_lights
    mode = "Lights" if adjusting_lights else "Room temp"
    print(f"Mode switched to: {mode}")
last_mode_switch_time = 0  # To debounce mode switch

def read_lights():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/3.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                latest_entry = feeds[-1]  # Get the most recent data
                lights_value = latest_entry.get("field3", default_lights)
                if lights_value is not None:
                    return int(float(lights_value))  # Convert to int
        print("No valid brightness value found in ThingSpeak response")
    except Exception as e:
        print(f"Failed to read brightness from ThingSpeak: {e}")
    return default_lights  # Default fallback

def read_room_temp():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/4.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                latest_entry = feeds[-1]  # Get the most recent data
                room_temp_value = latest_entry.get("field2", default_temp)
                if room_temp_value is not None:
                    return float(room_temp_value)
        print("No valid temperature value found in ThingSpeak response")
    except Exception as e:
        print(f"Failed to read temperature from ThingSpeak: {e}")
    return default_temp  # Default fallback

dutycycle = read_lights()
room_temp = read_room_temp()
last_publish_time = time.time()
last_distance_measurement_time = time.time()  # Track last distance measurement time

# variables
screens_state = 'closed'
dark_notified = False
cold_notified = False

# Timestamp for rate-limiting publish requests
last_publish_time = 0

# Initialize and activate LCD before anything else
ActivateLCD()
lcd_1 = LCD(PIN_OUT)
lcd_1.set_backlight(1)
lcd_1.go_to_xy(0, 0)
lcd_1.put_string('Room control')
lcd_1.go_to_xy(0, 10)
lcd_1.put_string('Screen status --> Checking')
lcd_1.refresh()
time.sleep(2)  # Allow time to read the initial message

# Clear LCD after displaying the message
lcd_1.clear()
lcd_1.refresh()

try:
    print('Start')
    print(f'lights: {dutycycle} %')
    print(f'room temp: {room_temp} °C')
    while True:

        # Detect mode switch button press
        if wiringpi.digitalRead(pin_switch_change) == 0:  # Active low
            if current_time - last_mode_switch_time > debounce_time:  # Simple debounce
                toggle_mode()
                last_mode_switch_time = current_time
            time.sleep(debounce_time)  # Debounce delay

        # Measure distance only every 15 seconds
        current_time = time.time()
        if current_time - last_distance_measurement_time >= 15:
            if adjusting_lights:
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
                print('Measured Distance =', round(distance, 1), 'cm')
                # If distance is less than 20 cm, set brightness to 10
                if distance < 20:
                    dutycycle = 10
                    print(f'lights: {dutycycle} %')
                last_distance_measurement_time = current_time  # Update last measurement time

        # Check if buttons are pressed (button reactions happen immediately)
        if wiringpi.digitalRead(pin_switch0) == 0:  # input is active low
            time.sleep(debounce_time)  # anti bouncing
            if adjusting_lights:
                dutycycle = int(numpy.clip(dutycycle + 10, 0, 100))
                print(f'lights: {dutycycle} %')
            else:
                room_temp = float(numpy.clip(room_temp + 0.5, 0, 50))
                print(f'room temp: {room_temp} °C')
        if wiringpi.digitalRead(pin_switch1) == 0:  # input is active low
            time.sleep(debounce_time)  # anti bouncing
            if adjusting_lights:
                dutycycle = int(numpy.clip(dutycycle - 10, 0, 100))
                print(f'lights: {dutycycle} %')
            else:
                room_temp = float(numpy.clip(room_temp - 0.5, 0, 50))
                print(f'room temp: {room_temp} °C')

        current_time = time.time()
        # Read Light Sensor (Lux) but DO NOT use it to control motor
        lux_value = get_value(bus, address_lightsensor)  # Get Lux reading
        lux_value = round(max(0, lux_value))  # Ensure no negative values
        temp_value = bmp280.get_temperature()

        # Convert Lux to Percentage (0-100%) - Only for display
        max_lux = 1000  # Define the maximum expected Lux value
        brightness_percent = int(numpy.clip((lux_value / max_lux) * 100, 0, 100))

        # Hysteresis Check
        if last_brightness == -1 or abs(brightness_percent - last_brightness) > hysteresis_threshold:
            last_brightness = brightness_percent  # Update stored value

        # Publish only every 15 seconds
        #current_time = time.time()
        if current_time - last_publish_time >= 15:
            MQTT_DATA = f"field1={lux_value}&field2={temp_value:.1f}&field3={dutycycle}&field4={room_temp:.1f}"
            print(MQTT_DATA)
            print("--------------------")
            print(f'Brightness: {lux_value} lux')
            print(f'Outside temp: {temp_value:.1f} °C')
            print(f'Lights: {dutycycle} %')
            print(f'Room temp: {room_temp:.1f} °C')
            print("--------------------")
            try:
                client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
                last_publish_time = current_time  # Update timestamp
            except OSError:
                client.reconnect()

        # PushOver message to phone
            if lux_value < 100:
                if not dark_notified:  # Send only if not already sent
                    conn = http.client.HTTPSConnection("api.pushover.net:443")
                    conn.request("POST", "/1/messages.json",
                        urllib.parse.urlencode({
                            "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                            "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                            "message": "Dark",
                        }), { "Content-type": "application/x-www-form-urlencoded" })
                    conn.getresponse()
                    dark_notified = True  # Mark as notified
            else:
                dark_notified = False # Reset if condition no longer holds

            if temp_value < 18:
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
                cold_notified = False  # Reset if condition no longer holds
                
        

        # Activate LCD to display values
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Brightness:{brightness_percent}%')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f"Temp Out:{temp_value:.1f}C")
        lcd_1.go_to_xy(0, 20)
        lcd_1.put_string(f'Lights:{dutycycle}%')
        lcd_1.go_to_xy(0, 30)
        lcd_1.put_string(f'Temp In:{room_temp}C')
        lcd_1.go_to_xy(0, 40)
        lcd_1.put_string(f'\nscreens {screens_state}')

        # Read brightness from ThingSpeak
        brightness = read_brightness()
        temperature = read_temperature()

        # Motor control logic ONLY based on ThingSpeak brightness
        if brightness > THRESHOLD and screens_state == 'open':
            lcd_1.put_string(f'\n--> closing')
            print('Closing screens')
            rotate_motor_threaded(100)  # Use threaded version
            screens_state = 'closed'  # Update state
        elif brightness <= THRESHOLD and screens_state == 'closed':
            lcd_1.put_string(f'\n--> opening')
            print('Opening screens')
            rotate_motor_reversed_threaded(100)  # Use threaded version
            screens_state = 'open'  # Update state

        lcd_1.refresh()
        DeactivateLCD()

        time.sleep(3)  # Update every 3 seconds

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
