from smbus2 import SMBus, i2c_msg
import time
import wiringpi as wp
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import datetime

plt.ion()

# Create an I2C bus object
bus = SMBus(0)
address = 0x23 #i2c address

# MQTT setup
MQTT_BROKER = "127.0.0.1"  # Change to your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/brightness"

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

# variables for plotting
time_axis = []
lux_value = []

# Main loop
while True:
    lux = round(read_bh1750())  # Read the lux value
    current_time = datetime.datetime.now()
    time_axis.append(current_time.strftime("%H:%M:%S"))
    lux_value.append(lux)
    print(f"Lux: {lux}")
    print(time_axis)
    print(lux_value)

    plt.clf()
    plt.figure(figsize=(7,6))
    plt.plot(time_axis, lux_value)
    plt.grid(True)
    plt.xlabel("Time")
    plt.ylabel("Lux")
    plt.title("Brightness sensor readings over time")
    plt.pause(0.1)


    # Publish the lux value to MQTT broker
    client.publish(MQTT_TOPIC, lux)

    client.loop()

    time.sleep(5)  # Wait 5 seconds before next reading
