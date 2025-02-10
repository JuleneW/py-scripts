
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
pin_switch_change = 12
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
wiringpi.pinMode(pin_switch_change, 0)
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

def read_thingspeak_WAARDES(field):
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID_WAARDES}/fields/{field}.json?api_key={THINGSPEAK_READ_API_KEY_WAARDES}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            #print("ThingSpeak Response:", data)  # Debugging output
            feeds = data.get("feeds", [])
            if feeds and feeds[-1].get(f"field{field}") is not None:
                return float(feeds[-1][f"field{field}"])
            else:
                #print(f"Warning: No data for field {field}")
                return 0
    except Exception as e:
        #print(f"Failed to read from ThingSpeak: {e}")
        print(0)
    return 0

rooms_WAARDE = [f'room_{i}_WAARDE' for i in range(1, 9)] # list of room names
for room in rooms_WAARDE:
    room = [f'float(read_thingspeak_WAARDE({i}))' for i in range(1, 9)]

def read_thingspeak_GEWENST(field):
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID_GEWENST}/fields/{field}.json?api_key={THINGSPEAK_READ_API_KEY_GEWENST}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            #print("ThingSpeak Response (GEWENST):", data)  # Debugging output
            feeds = data.get("feeds", [])
            if feeds and feeds[-1].get(f"field{field}") is not None:
                return float(feeds[-1][f"field{field}"])
            else:
                #print(f"Warning: No data for field {field} in GEWENST channel")
                return 0
    except Exception as e:
        #print(f"Failed to read from ThingSpeak (GEWENST): {e}")
        print(0)
    return 0

rooms_GEWENST = [f'room_{i}_GEWENST' for i in range(1, 9)] # list of room names
for room in rooms_GEWENST:
    room = [f'float(read_thingspeak_GEWENST({i}))' for i in range(1, 9)]

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

current_index = 4 # start with my own room
last_mode_switch_time = 0  # To debounce mode switch

def toggle_room():
    global current_index
    current_index = (current_index + 1) % len(rooms_GEWENST)  # Cycle through rooms
    print(f"Active room: {rooms_GEWENST[current_index]}")  # Replace with actual logic

def handle_switches():
    global current_index, last_mode_switch_time
    while running:
        current_time = time.time()

        # Detect toggle switch button press
        if wiringpi.digitalRead(pin_switch_change) == 0:  # Active low
            if current_time - last_mode_switch_time > debounce_time:  # Simple debounce
                toggle_room()
                last_mode_switch_time = current_time
            time.sleep(debounce_time)  # Debounce delay

        active_room = rooms_GEWENST[current_index] # get active room
        field_number = current_index + 1  # Map room_1_GEWENST → field1, etc.

        # Read current value from ThingSpeak
        current_value = read_thingspeak_GEWENST(field_number)

        # Check if buttons are pressed (button reactions happen immediately)
        if wiringpi.digitalRead(pin_switch0) == 0:  # input is active low
            time.sleep(debounce_time)  # Anti bouncing
            new_value = float(numpy.clip(current_value + 1, 0, 50))
            print("----------------------------")
            print(f'Change value of {active_room} to: {new_value:.1f}')

            # Publish updated value to ThingSpeak
            MQTT_DATA_GEWENST = f"field{field_number}={new_value:.1f}"
            client.publish(topic=MQTT_TOPIC_GEWENST, payload=MQTT_DATA_GEWENST, qos=0, retain=False)

        if wiringpi.digitalRead(pin_switch1) == 0:  # input is active low
            time.sleep(debounce_time)  # Anti bouncing
            new_value = float(numpy.clip(current_value - 1, 0, 50))
            print("----------------------------")
            print(f'Change value of {active_room} to: {new_value:.1f}')

            # Publish updated value to ThingSpeak
            MQTT_DATA_GEWENST = f"field{field_number}={new_value:.1f}"
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
    time.sleep(1)
    print('start')
    while True:
        # get sensor values at start of every loop
        sens_temperature_value = bmp280.get_temperature()

        # publish sensor value to ThingSpeak channel WAARDES field 5
        MQTT_DATA_WAARDES = f"field5={sens_temperature_value:.1f}"
        try:
            client.publish(topic=MQTT_TOPIC_WAARDES, payload=MQTT_DATA_WAARDES, qos=0, retain=False)
        except OSError:
            client.reconnect()

        print("----------------------------")
        print(f'My room temp: {read_thingspeak_WAARDES(5):.1f} °C')
        print(f'My desired room temp: {read_thingspeak_GEWENST(5):.1f} °C')

        # Display values on LCD
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Thermostat')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f'Temp: {read_thingspeak_GEWENST(5):.1f} °C')
        lcd_1.go_to_xy(0, 20)
        lcd_1.put_string(f'--> {read_thingspeak_GEWENST(5):.1f} °C')

        # Motor control logic ONLY based on ThingSpeak temp
        if read_thingspeak_WAARDES(5) > threshold and screens_state == 'open':
            lcd_1.go_to_xy(0, 40)
            lcd_1.put_string(f'--> closing')
            print("----------------------------")
            print('Closing screens')
            rotate_motor_threaded(100)  # Use threaded version
            screens_state = 'closed'  # Update state
        elif read_thingspeak_WAARDES(5) <= threshold and screens_state == 'closed':
            lcd_1.go_to_xy(0, 40)
            lcd_1.put_string(f'--> opening')
            print("----------------------------")
            print('Opening screens')
            rotate_motor_reversed_threaded(100)  # Use threaded version
            screens_state = 'open'  # Update state

        print("----------------------------")
        print("Overview all rooms:")
        print(f'R1 = {read_thingspeak_WAARDES(1):.1f} °C     R2 = {read_thingspeak_WAARDES(2):.1f} lux')
        print(f'R3 = {read_thingspeak_WAARDES(3):.1f} lux    R4 = {read_thingspeak_WAARDES(4):.1f} °C')
        print(f'R5 = {read_thingspeak_WAARDES(5):.1f} °C    R6 = {read_thingspeak_WAARDES(6):.1f} lux')
        print(f'R7 = {read_thingspeak_WAARDES(7):.1f} lux    R8 = {read_thingspeak_WAARDES(8):.1f} lux')

        lcd_1.refresh()
        DeactivateLCD()    

        # PushOver message to phone
        if read_thingspeak_WAARDES(5) > threshold:
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