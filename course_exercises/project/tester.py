import time
import wiringpi
import numpy
import sys
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

# Pin definitions
pin_switch0 = 3         # button for value down
pin_switch1 = 4         # button for value up
pin_switch_change = 12  # Mode toggle button
pin_CS_lcd = 15         # chip select pin for LCD
pinTrg = 16             # Trigger pin for ultrasone module
pinEcho = 13            # Echo pin for ultrasone module
PIN_OUT = {             # LCD pins
    'SCLK': 14,
    'DIN': 11,
    'DC': 9,
    'CS': 15,
    'RST': 10,
    'LED': 6,           # backlight
}
pin_A = 2 # gpio pin for coil A of stepper motor
pin_B = 5 # gpio pin for coil B of stepper motor
pin_C = 7 # gpio pin for coil C of stepper motor
pin_D = 8 # gpio pin for coil D of stepper motor

# variables for pins
debounce_time = 0.1  # Reduced debounce time for quicker button response

# Setup WiringPi
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin_switch0, 0)
wiringpi.pinMode(pin_switch1, 0)
wiringpi.pinMode(pin_switch_change, 0)
wiringpi.pinMode(pin_CS_lcd, 1)
wiringpi.pinMode(pinTrg, 1) 
wiringpi.pinMode(pinEcho, 0) 
wiringpi.pinMode(pin_A, 1)
wiringpi.pinMode(pin_B, 1)
wiringpi.pinMode(pin_C, 1)
wiringpi.pinMode(pin_D, 1)

# Stepper motor sequence for full step
full_step_sequence = [
    [1, 0, 0, 1, 1, 0, 0, 1],  # Step 1: Coil A
    [1, 1, 0, 0, 1, 1, 0, 0],  # Step 2: Coil B
    [0, 1, 1, 0, 0, 1, 1, 0],  # Step 3: Coil C
    [0, 0, 1, 1, 0, 0, 1, 1],  # Step 4: Coil D
]

# Stepper motor functions
# Function to perform a single step
def perform_step(step_sequence):
    wiringpi.digitalWrite(pin_A, step_sequence[0])
    wiringpi.digitalWrite(pin_B, step_sequence[1])
    wiringpi.digitalWrite(pin_C, step_sequence[2])
    wiringpi.digitalWrite(pin_D, step_sequence[3])

def rotate_motor(number_steps):
    def motor_task():
        for i in range(number_steps):
            for step in full_step_sequence:
                perform_step(step)
                time.sleep(0.01)  # Step delay
    # Start motor in a new thread
    motor_thread = threading.Thread(target=motor_task)
    motor_thread.start()

def rotate_motor_reversed(number_steps):
    def motor_task():
        for i in range(number_steps - 1, -1, -1):
            for step in full_step_sequence:
                perform_step(step)
                time.sleep(0.01)  # Step delay
    # Start motor in a new thread
    motor_thread = threading.Thread(target=motor_task)
    motor_thread.start()

# LCD Functions
def ActivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 0)
    time.sleep(0.000005)

def DeactivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 1)
    time.sleep(0.000005)

# Sensor variables
threshold = 200     # Threshold in lux
last_brightness = -1  # Initialize with an impossible value
hysteresis = 5  # Minimum change required to update
default_value_light = 50 # default value of room light
default_value_temp = 20  # default value of room temp

# Sensor functions
# BH1750
def get_lux():
    write = i2c_msg.write(address_lightsensor, [0x10])
    read = i2c_msg.read(address_lightsensor, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return (((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2

# BMP280
def get_temperature():
    return bmp280.get_temperature()

# Read values from ThingSpeak fields 1 & 2 to display on LCD (sensors), fields 3 & 4 for room value adjustments
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

# Read variables
brightness_value = read_thingspeak(1)
temperature_value = read_thingspeak(2)
desired_room_light = int(read_thingspeak(3))
desired_room_temp = int(read_thingspeak(4))

# Mode Toggle
adjusting_brightness = True
def toggle_mode():
    global adjusting_brightness
    adjusting_brightness = not adjusting_brightness
    mode = "Brightness" if adjusting_brightness else "Temperature"
    print(f"Mode switched to: {mode}")
last_mode_switch_time = 0       # To debounce mode switch

# Other variables
screens_state = 'closed'
last_publish_time = 0   # Timestamp for rate-limiting publish requests
last_publish_time = time.time()
last_distance_measurement_time = time.time()  # Track last distance measurement time

# Initialize and activate LCD before anything else
ActivateLCD()
lcd_1 = LCD(PIN_OUT)
lcd_1.set_backlight(1)
lcd_1.put_string('Screen status --> Checking')
lcd_1.refresh()
time.sleep(2)  # Allow time to read the initial message
# Clear LCD after displaying the message
lcd_1.clear()
lcd_1.refresh()

# main loop
try:
    print('Start')
    #print(f'Sunlight: {sens_brightness_value:.1f} lux')
    #print(f'Outside temp: {sens_temperature_value:.1f} °C')
    #print(f'Room lights: {desired_room_light:.1f} lux')
    #print(f'Room temp: {desired_room_temp:.1f} °C')
    while True:
        current_time = time.time()

        # Read sensors
        sens_brightness_value = get_lux()
        sens_temperature_value = get_temperature()

        # Convert Lux to Percentage (0-100%) - Only for LCD display
        #max_lux = 1000  # Define the maximum expected Lux value
        #brightness_percent = int(numpy.clip((brightness_value / max_lux) * 100, 0, 100))

        # Hysteresis Check
        if last_brightness == -1 or abs(sens_brightness_value - last_brightness) > hysteresis:
            last_brightness = brightness_value  # Update stored value

        # Detect mode switch toggle button press
        if wiringpi.digitalRead(pin_switch_change) == 0:  # Active low
            if current_time - last_mode_switch_time > debounce_time:  # Simple debounce
                toggle_mode()
                last_mode_switch_time = current_time
            time.sleep(debounce_time)  # Debounce delay
        
        # Check if buttons are pressed (button reactions happen immediately)
        if wiringpi.digitalRead(pin_switch0) == 0:  # input is active low
            time.sleep(debounce_time)  # anti bouncing
            if adjusting_brightness:
                desired_room_light = min(desired_room_light + 10, 100)
                print(f'Room lights: {desired_room_light}')
            else:
                desired_room_temp = min(desired_room_temp + 0.5, 50)
                print(f'Room temp: {desired_room_temp} °C')
        if wiringpi.digitalRead(pin_switch1) == 0:  # input is active low
            time.sleep(debounce_time)  # anti bouncing
            if adjusting_brightness:
                desired_room_light = min(desired_room_light + 10, 100)
                print(f'Room lights: {desired_room_light}')
            else:
                desired_room_temp = min(desired_room_temp + 0.5, 50)
                print(f'Room temp: {desired_room_temp} °C')

        # Measure distance - only every 15 seconds
        if current_time - last_distance_measurement_time >= 15:
            #if adjusting_brightness:
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
                desired_room_light = 10
                print(f'lights: {desired_room_light}')
            last_distance_measurement_time = current_time  # Update last measurement time
        
        # Publish only every 15 seconds
        if current_time - last_publish_time >= 15:
            MQTT_DATA = (f"field1={sens_brightness_value:.1f}&field2={sens_temperature_value:.1f}&field3={desired_room_light}&field4={desired_room_temp:.1f}")
            print("--------------------")
            print(f'Sunlight: {sens_brightness_value:.1f} lux')
            print(f'Outside temp: {sens_temperature_value:.1f} °C')
            print(f'Room lights: {desired_room_light} %')
            print(f'Room temp: {desired_room_temp:.1f} °C')
            print("--------------------")
            try:
                client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
            except OSError:
                client.reconnect()
            last_publish_time = current_time  # Update timestamp
            time.sleep(0.1)  # Small delay to keep the loop responsive

            # PushOver message to phone
            if brightness_value < 100:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Dark",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
            if temperature_value < 18:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Cold",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()

        # Activate LCD to display values
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Sun:{brightness_value}lux')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f"Temp out:{temperature_value:.1f}C")
        lcd_1.go_to_xy(0, 20)
        lcd_1.put_string(f"Lights:{desired_room_light}%")
        lcd_1.go_to_xy(0, 30)
        lcd_1.put_string(f"Temp in:{desired_room_temp:.1f}C")
        #lcd_1.go_to_xy(0, 40)
        lcd_1.put_string(f'\nscreens {screens_state}')

        # Motor control logic ONLY based on ThingSpeak brightness
        if brightness_value > threshold and screens_state == 'open':
            lcd_1.put_string(f'\n--> closing')
            print('Closing screens')
            rotate_motor(100)
            screens_state = 'closed'  # Update state
        elif brightness_value <= threshold and screens_state == 'closed':
            lcd_1.put_string(f'\n--> opening')
            print('Opening screens')
            rotate_motor_reversed(100)
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