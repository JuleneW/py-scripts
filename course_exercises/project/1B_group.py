import time
import wiringpi
import numpy
import spidev
from ClassLCD import LCD
import paho.mqtt.client as mqtt
from smbus2 import SMBus, i2c_msg
import requests
import threading

# Initialize I2C Bus
bus = SMBus(0)
address = 0x23  # i2c address

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "channels/2792379/publish"
MQTT_CLIENT_ID = "MS4nJTksJgwXHywIAhUUOxs"
MQTT_USER = "MS4nJTksJgwXHywIAhUUOxs"
MQTT_PWD = "rywz2S3vL/h5WswSrmMmIoNM"

# ThingSpeak Read API Key
THINGSPEAK_READ_API_KEY = "0OOB9HY94B6XQ63M"
THINGSPEAK_CHANNEL_ID = "2792379"

# Threshold in lux
THRESHOLD = 200

# Pin definitions
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

# Hysteresis Variables
last_brightness = -1  # Initialize with an impossible value
hysteresis_threshold = 5  # Minimum change required to update
default_value = 50

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

# Setup BH1750
bus.write_byte(address, 0x10)

def get_value(bus, address):
    write = i2c_msg.write(address, [0x10])  # 1lx resolution 120ms see datasheet
    read = i2c_msg.read(address, 2)
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

ActivateLCD()
lcd_1 = LCD(PIN_OUT)
time.sleep(0.1)

def read_brightness():
    url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/5.json?api_key={THINGSPEAK_READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                latest_entry = feeds[-1]  # Get the most recent data
                brightness_value = latest_entry.get("field5", default_value)
                if brightness_value is not None:
                    return int(float(brightness_value))  # Convert to int
        print("No valid brightness value found in ThingSpeak response")
    except Exception as e:
        print(f"Failed to read brightness from ThingSpeak: {e}")

    return default_value  # Default fallback

#screens_open = False
screens_state = 'closed'

# Timestamp for rate-limiting publish requests
last_publish_time = 0

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


try:
    print('Start')
    while True:
        # Read Light Sensor (Lux) but DO NOT use it to control motor
        lux_value = get_value(bus, address)  # Get Lux reading
        lux_value = round(max(0, lux_value))  # Ensure no negative values

        # Convert Lux to Percentage (0-100%) - Only for display
        max_lux = 1000  # Define the maximum expected Lux value
        brightness_percent = int(numpy.clip((lux_value / max_lux) * 100, 0, 100))

        # Hysteresis Check
        if last_brightness == -1 or abs(brightness_percent - last_brightness) > hysteresis_threshold:
            last_brightness = brightness_percent  # Update stored value

        # Publish only every 15 seconds
        current_time = time.time()
        if current_time - last_publish_time >= 15:
            MQTT_DATA = f"field5={lux_value}"
            print(MQTT_DATA)
            print("--------------------")
            try:
                client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
                last_publish_time = current_time  # Update timestamp
            except OSError:
                client.reconnect()

        # Read brightness from ThingSpeak
        brightness = read_brightness()
        #print(brightness)

        # Activate LCD to display values
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Brightness:{brightness_percent}%')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f'\nscreens {screens_state}')

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
