import time
from smbus2 import SMBus
from bmp280 import BMP280  # Import the BMP280 library
import paho.mqtt.client as mqtt

# Initialize I2C bus
bus = SMBus(0)  # Use I2C bus 1 on most Raspberry Pi/Orange Pi boards
address_lightsensor = 0x23
address_tempsensor = 0x77

# Initialize the BMP280 sensor
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address_tempsensor)  # Default I2C address (0x76 or 0x77)

# MQTT setup
MQTT_BROKER = "test.mosquitto.org"  # Change to your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "test/channel"

# Initialize MQTT client
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 1883)
# client.subscribe("MQTT_TOPIC")

# Function to read from BH1750 sensor
def read_bh1750():
    bus.write_byte(address_lightsensor, 0x10)  # Start measurement in continuous mode
    time.sleep(0.2)  # Wait for measurement to complete
    data = bus.read_i2c_block_data(address_lightsensor, 0x23, 2)
    lux = (data[0] << 8 | data[1]) / 1.2  # Convert raw data to lux
    return lux

while True:
    # Read lux, temperature and pressure
    lux = read_bh1750()
    temperature = bmp280.get_temperature()
    pressure = bmp280.get_pressure()
    sea_level_pressure = 997
    altitude = 44330.0 * (1.0 - (pressure / sea_level_pressure) ** (1.0 / 5.255))

     # Format values to two decimal places
    formatted_lux = f"Lux: {lux:.2f} lux"
    formatted_temperature = f"Temperature: {temperature:.2f} °C"
    formatted_pressure = f"Pressure: {pressure:.2f} hPa"
    formatted_altitude = f"Altitude: {altitude:.2f} m"

    # Display the results
    print(formatted_lux)
    print(formatted_temperature)
    print(formatted_pressure)
    print(formatted_altitude)
    print()

    # Publish the results to MQTT broker
    client.publish(MQTT_TOPIC, formatted_lux)
    client.publish(MQTT_TOPIC, formatted_temperature)
    client.publish(MQTT_TOPIC, formatted_pressure)
    client.publish(MQTT_TOPIC, formatted_altitude)
    client.publish(MQTT_TOPIC, "------")
    client.loop()

    # Sleep for 3 seconds
    time.sleep(3)