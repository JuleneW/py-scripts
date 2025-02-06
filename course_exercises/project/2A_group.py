import time
import wiringpi
import numpy
import paho.mqtt.client as mqtt
import requests

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "channels/2792381/publish"
MQTT_CLIENT_ID = "MS4nJTksJgwXHywIAhUUOxs"
MQTT_USER = "MS4nJTksJgwXHywIAhUUOxs"
MQTT_PWD = "rywz2S3vL/h5WswSrmMmIoNM"

# ThingSpeak Read API Key
THINGSPEAK_READ_API_KEY = "94U2IKT6YRPREMPN"
THINGSPEAK_CHANNEL_ID = "2792381"

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

#Setup
pin_led = 12
pin_switch0 = 3
pin_switch1 = 4
debounce_time = 0.3
wiringpi.wiringPiSetup() 

# Set pin as a softPWM output
wiringpi.softPwmCreate(pin_led, 0, 100)

# Set pins as a input
wiringpi.pinMode(pin_switch0, 0)
wiringpi.pinMode(pin_switch1, 0)

default_value = 50

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

# Start PWM
dutycycle = read_brightness()
wiringpi.softPwmWrite(pin_led, dutycycle)

last_publish_time = time.time()  # Track last MQTT publish time

try:
    print("Start")
    print(f'lights: {dutycycle} %')
    while True:
        if(wiringpi.digitalRead(pin_switch0) == 0): # input is active low
            time.sleep(debounce_time) # anti bouncing
            dutycycle = int(numpy.clip(dutycycle+10, 0, 100))
            print(f'lights: {dutycycle} %')
        if(wiringpi.digitalRead(pin_switch1) == 0): # input is active low
            time.sleep(debounce_time) # anti bouncing
            dutycycle = int(numpy.clip(dutycycle-10, 0, 100))
            print(f'lights: {dutycycle} %')
        # Publish MQTT only every 15 seconds (4 times per minute)
        if time.time() - last_publish_time >= 15:
            MQTT_DATA = f"field5={dutycycle}"
            try:
                client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
            except OSError:
                client.reconnect()
            last_publish_time = time.time()
        # Apply PWM to LED
        wiringpi.softPwmWrite(pin_led, dutycycle)
        time.sleep(0.1)  # Keep loop responsive
except KeyboardInterrupt:
    wiringpi.softPwmWrite(pin_led, 0)            # stop the white PWM output
    print("\nDone")