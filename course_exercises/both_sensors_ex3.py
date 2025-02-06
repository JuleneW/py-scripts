import time
from bmp280 import BMP280
from smbus2 import SMBus
import paho.mqtt.client as mqtt

# Create an I2C bus object
bus = SMBus(0)
address_tempsensor = 0x77
address_lightsensor = 0x23

# Setup BMP280
bmp280 = BMP280(i2c_addr= address_tempsensor, i2c_dev=bus)
interval = 15 # Sample period in seconds

# MQTT settings
MQTT_HOST ="mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL =60
MQTT_TOPIC = "channels/2796018/publish"
MQTT_CLIENT_ID = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_USER = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_PWD = "+cm5H5ON/XwqDbHqx0puzrUG"


def on_connect(client, userdata, flags, rc):
    if rc==0:
        print("Connected OK with result code "+str(rc))
    else:
        print("Bad connection with result code "+str(rc))

def on_disconnect(client, userdata, flags, rc=0):
    print("Disconnected result code "+str(rc))

def on_message(client,userdata,msg):
    print("Received a message on topic: " + msg.topic + "; message: " + msg.payload)


# Set up a MQTT Client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)

# Connect callback handlers to client
client.on_connect= on_connect
client.on_disconnect= on_disconnect
client.on_message= on_message

print("Attempting to connect to %s" % MQTT_HOST)
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start() #start the loop

# Function to read from BH1750 sensor
def read_bh1750():
    bus.write_byte(address_lightsensor, 0x10)  # Start measurement in continuous mode
    time.sleep(0.2)  # Wait for measurement to complete
    data = bus.read_i2c_block_data(address_lightsensor, 0x23, 2)
    lux = (data[0] << 8 | data[1]) / 1.2  # Convert raw data to lux
    return lux

while True:
    # Measure data
    bmp280_temperature = bmp280.get_temperature()
    bmp280_pressure = bmp280.get_pressure()
    #sea_level_pressure = 997
    #altitude = 44330.0 * (1.0 - (pressure / sea_level_pressure) ** (1.0 / 5.255))
    bh1750_brightness = read_bh1750()

    print("Temperature: %4.1f, Pressure: %4.1f, Brightness: %4.1f" % (bmp280_temperature, bmp280_pressure, bh1750_brightness))
    # Create the JSON data structure
    MQTT_DATA = "field1="+str(bmp280_temperature)+"&field2="+str(bmp280_pressure)+"&field3="+str(bh1750_brightness)+"&status=MQTTPUBLISH"
    print(MQTT_DATA)
    try:
        client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False, properties=None)
        time.sleep(interval)
    except OSError:
        client.reconnect()
