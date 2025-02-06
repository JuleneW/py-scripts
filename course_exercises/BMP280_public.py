import time
from smbus2 import SMBus
from bmp280 import BMP280  # Import the BMP280 library
import paho.mqtt.client as mqtt

# Initialize I2C bus
bus = SMBus(0)  # Use I2C bus 1 on most Raspberry Pi/Orange Pi boards
address = 0x77

# Initialize the BMP280 sensor
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address)  # Default I2C address (0x76 or 0x77)

# MQTT setup
MQTT_BROKER = "test.mosquitto.org"  # Change to your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "test/channel"

# Initialize MQTT client
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 1883)
# client.subscribe("MQTT_TOPIC")

while True:
    # Read temperature and pressure
    temperature = bmp280.get_temperature()
    pressure = bmp280.get_pressure()
    sea_level_pressure = 996.1
    altitude = 44330.0 * (1.0 - (pressure / sea_level_pressure) ** (1.0 / 5.255))

     # Format values to two decimal places
    formatted_temperature = f"{temperature:.2f}"
    formatted_pressure = f"{pressure:.2f}"
    formatted_altitude = f"{altitude:.2f}"

    # Display the results
    print("Temperature:", formatted_temperature, "°C")
    print("Pressure:, ", formatted_pressure, "hPa")
    print("Altitude:", formatted_altitude, "m")

    # Publish the results to MQTT broker
    client.publish(MQTT_TOPIC, formatted_temperature)
    client.publish(MQTT_TOPIC, formatted_pressure)
    client.publish(MQTT_TOPIC, formatted_altitude)
    client.loop()

    # Sleep for 3 seconds
    time.sleep(3)