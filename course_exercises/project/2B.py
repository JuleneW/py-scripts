import time
import wiringpi
import sys
import numpy
import spidev
from ClassLCD import LCD
import paho.mqtt.client as mqtt
import requests

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "channels/2823966/publish"
MQTT_CLIENT_ID = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_USER = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_PWD = "+cm5H5ON/XwqDbHqx0puzrUG"

# ThingSpeak Read API Key
THINGSPEAK_READ_API_KEY = "UQNRBSBPHN4J85WX"
THINGSPEAK_CHANNEL_ID = "2823966"

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

# Pin initialisation
pin_switch_change = 12
pin_switch0 = 3
pin_switch1 = 4
debounce_time = 0.1  # Reduced debounce time for quicker button response
pinTrg = 16
pinEcho = 13
pin_CS_lcd = 15

# Pin definitions
PIN_OUT = {
    'SCLK': 14,
    'DIN': 11,
    'DC': 9,
    'CS': 15,
    'RST': 10,
    'LED': 6,  # backlight
}

# Setup
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin_switch_change, 0)
wiringpi.pinMode(pin_switch0, 0)                  # Set pins as input
wiringpi.pinMode(pin_switch1, 0)
wiringpi.pinMode(pinTrg, 1)                       # Set pin to mode 1 (OUTPUT)
wiringpi.pinMode(pinEcho, 0)                      # Set pin to mode 0 (INPUT)
wiringpi.pinMode(pin_CS_lcd, 1)  # Set pin to mode 1 (OUTPUT)

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
lcd_1.put_string('Room control')
lcd_1.refresh()
time.sleep(2)  # Allow time to read the initial message

# Clear LCD after displaying the message
lcd_1.clear()
lcd_1.refresh()

# Variables
default_value = 50
default_temp = 20
adjusting_brightness = True # Start in brightness adjustment mode

def toggle_mode():
    global adjusting_brightness
    adjusting_brightness = not adjusting_brightness
    mode = "Brightness" if adjusting_brightness else "Temperature"
    print(f"Mode switched to: {mode}")

last_mode_switch_time = 0  # To debounce mode switch

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
                temp_value = latest_entry.get("field2", default_temp)
                if temp_value is not None:
                    return float(temp_value)
        print("No valid temperature value found in ThingSpeak response")
    except Exception as e:
        print(f"Failed to read temperature from ThingSpeak: {e}")
    return default_temp  # Default fallback

dutycycle = read_brightness()
temperature = read_temperature()

last_publish_time = time.time()
last_distance_measurement_time = time.time()  # Track last distance measurement time

try:
    print("Start")
    print(f'lights: {dutycycle} %')
    print(f'Temp: {temperature} °C')
    while True:
        current_time = time.time()

        # Activate LCD to display values
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string(f'Lights:{dutycycle}%')
        lcd_1.go_to_xy(0, 10)
        lcd_1.put_string(f"Temp:{temperature:.1f}C")

        # Detect mode switch button press
        if wiringpi.digitalRead(pin_switch_change) == 0:  # Active low
            if current_time - last_mode_switch_time > debounce_time:  # Simple debounce
                toggle_mode()
                last_mode_switch_time = current_time
            time.sleep(debounce_time)  # Debounce delay

        # Measure distance only every 15 seconds
        if current_time - last_distance_measurement_time >= 15:
            if adjusting_brightness:
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
            if adjusting_brightness:
                dutycycle = int(numpy.clip(dutycycle + 10, 0, 100))
                print(f'lights: {dutycycle} %')
            else:
                temperature = float(numpy.clip(temperature + 0.5, 0, 50))
                print(f'temperature: {temperature} °C')

        if wiringpi.digitalRead(pin_switch1) == 0:  # input is active low
            time.sleep(debounce_time)  # anti bouncing
            if adjusting_brightness:
                dutycycle = int(numpy.clip(dutycycle - 10, 0, 100))
                print(f'lights: {dutycycle} %')
            else:
                temperature = float(numpy.clip(temperature - 0.5, 0, 50))
                print(f'temperature: {temperature} °C')

        # Publish data every 15 seconds
        if current_time - last_publish_time >= 15:
            MQTT_DATA = f"field1={dutycycle}&field2={temperature}"
            try:
                client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
            except OSError:
                client.reconnect()
            last_publish_time = current_time

        lcd_1.refresh()
        DeactivateLCD()

        time.sleep(0.1)  # Small delay to keep the loop responsive

except KeyboardInterrupt:
    ActivateLCD()
    lcd_1.clear()
    lcd_1.refresh()
    lcd_1.set_backlight(0)
    DeactivateLCD()
    print("\nDone")
