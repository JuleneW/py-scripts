from smbus2 import SMBus, i2c_msg
import time
import wiringpi as wp
import paho.mqtt.client as mqtt

# Create an I2C bus object
bus = SMBus(0)
address = 0x23 #i2c address

# LED setup (using WiringPi pin numbering)
LED_A_PIN = 3  # GPIO 3 (WiringPi pin)
LED_B_PIN = 4  # GPIO 4 (WiringPi pin)

# Initialize WiringPi and set pins to output
wp.wiringPiSetup()
wp.pinMode(LED_A_PIN, 1)  # Set GPIO 3 as output
wp.pinMode(LED_B_PIN, 1)  # Set GPIO 4 as output

# MQTT setup
MQTT_BROKER = "127.0.0.1"  # Change to your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/brightness"

# Threshold for BH1750 in lux
THRESHOLD = 300

# Initialize MQTT client
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 1883)
# client.subscribe("MQTT_TOPIC")

# Function to read from BH1750 sensor
def read_bh1750():
    bus.write_byte(address, 0x10)  # Start measurement in continuous mode
    time.sleep(0.2)  # Wait for measurement to complete
    data = bus.read_i2c_block_data(address, 0x23, 2)
    lux = (data[0] << 8 | data[1]) / 1.2  # Convert raw data to lux
    return lux

# Main loop
try:
    while True:
        lux = read_bh1750()  # Read the lux value
        print(f"Lux: {lux}")

        if lux > THRESHOLD:
            wp.digitalWrite(LED_A_PIN, 1)  # Turn on LED A
            wp.digitalWrite(LED_B_PIN, 0)  # Turn off LED B
        else:
            wp.digitalWrite(LED_A_PIN, 0)  # Turn off LED A
            wp.digitalWrite(LED_B_PIN, 1)  # Turn on LED B

        # Publish the lux value to MQTT broker
        client.publish(MQTT_TOPIC, lux)

        client.loop()

        time.sleep(1)  # Wait 1 second before next reading

except KeyboardInterrupt:
    pass

finally:
    # Turn off LEDs before exiting
    wp.digitalWrite(LED_A_PIN, 0)
    wp.digitalWrite(LED_B_PIN, 0)