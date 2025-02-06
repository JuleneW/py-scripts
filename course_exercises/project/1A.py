import time
import wiringpi
import numpy
import spidev
from ClassLCD import LCD
import paho.mqtt.client as mqtt
from smbus2 import SMBus, i2c_msg
from bmp280 import BMP280
import http.client, urllib # for PushOver messages

# Initialize I2C Bus
bus = SMBus(0)
address_lightsensor = 0x23  # i2c address
address_tempsensor = 0x77
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address_tempsensor)

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "channels/2821967/publish"
MQTT_CLIENT_ID = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_USER = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_PWD = "+cm5H5ON/XwqDbHqx0puzrUG"

# Pin definitions
PIN_OUT = {
    'SCLK': 14,
    'DIN': 11,
    'DC': 9,
    'CS': 15,
    'RST': 10,
    'LED': 6,  # backlight
}
pin_CS_lcd = 15

# Setup WiringPi
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin_CS_lcd, 1)  # Set pin to mode 1 (OUTPUT)

# Hysteresis Variables
last_brightness = -1  # Initialize with an impossible value
hysteresis_threshold = 5  # Minimum change required to update

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
bus.write_byte(address_lightsensor, 0x10)

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

try:
    print('Start')
    lcd_1.clear()
    lcd_1.set_backlight(1)
    while True:
        # Read Sensors
        lux_value = get_value(bus, address_lightsensor)  # Get Lux reading
        lux_value = round(max(0, lux_value))  # Ensure no negative values
        temp_value = bmp280.get_temperature()

        # Convert Lux to Percentage (0-100%)
        max_lux = 1000  # Define the maximum expected Lux value
        brightness_percent = int(numpy.clip((lux_value / max_lux) * 100, 0, 100))

        # Hysteresis Check
        if last_brightness == -1 or abs(brightness_percent - last_brightness) > hysteresis_threshold:
            last_brightness = brightness_percent  # Update stored value

            # Update LCD Display
            ActivateLCD()
            lcd_1.clear()
            lcd_1.go_to_xy(0, 0)
            lcd_1.put_string(f'Brightness:{brightness_percent}%')
            lcd_1.put_string(f'Temp:{temp_value:.1f}°C')
            lcd_1.refresh()
            DeactivateLCD()

            # Publish to ThingSpeak (Lux Value)
            MQTT_DATA = f"field1={lux_value}&field2={temp_value:.1f}"
            # MQTT_DATA = f"field1=\n\n{brightness_percent}%\n\n&status=MQTTPUBLISH"
            print(MQTT_DATA)
            print("--------------------")
            try:
                client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
            except OSError:
                client.reconnect()

            # PushOver message to phone
            if lux_value < 100:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Dark",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
            if temp_value < 18:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "ae1d36igbzin3m1ue52u2eydcjjgaf",
                        "user": "ukzzn5v59252yvktrykor8ymqr6p8n",
                        "message": "Cold",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()

        time.sleep(15)  # Update every 15 seconds

except KeyboardInterrupt:
    ActivateLCD()
    lcd_1.clear()
    lcd_1.refresh()
    lcd_1.set_backlight(0)
    DeactivateLCD()
    print("\nShutdown complete.")
