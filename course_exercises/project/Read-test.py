import time
import wiringpi
import numpy
import spidev
from ClassLCD import LCD
import paho.mqtt.client as mqtt
from smbus2 import SMBus, i2c_msg
import requests

# Initialize I2C Bus
bus = SMBus(0)
address = 0x23  # i2c address

# Setup BH1750
bus.write_byte(address, 0x10)

def get_value(bus, address):
    write = i2c_msg.write(address, [0x10])  # 1lx resolution 120ms see datasheet
    read = i2c_msg.read(address, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return (((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2  # Conversion

while True:
        # Read Light Sensor (Lux) but DO NOT use it to control motor
        lux_value = get_value(bus, address)  # Get Lux reading
        print(f'{lux_value:.2f}')
        time.sleep(0.5)