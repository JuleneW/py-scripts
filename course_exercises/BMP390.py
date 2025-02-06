from smbus2 import SMBus
import time

# BMP390 address and registers
BMP390_ADDRESS = 0x77
BMP390_CHIP_ID_REG = 0x00
BMP390_CHIP_ID = 0x60  # Expected chip ID for BMP390
BMP390_CTRL_MEAS = 0x1B
BMP390_CONFIG = 0x1C
BMP390_PRESS_MSB = 0x04
BMP390_TEMP_MSB = 0x07

def bmp390_init(bus):
    # Configure the sensor
    bus.write_byte_data(BMP390_ADDRESS, BMP390_CTRL_MEAS, 0x33)  # Normal mode, pressure + temp oversampling

def bmp390_read(bus):
    # Read raw pressure and temperature data
    press_data = bus.read_i2c_block_data(BMP390_ADDRESS, BMP390_PRESS_MSB, 3)
    temp_data = bus.read_i2c_block_data(BMP390_ADDRESS, BMP390_TEMP_MSB, 3)
    
    # Convert raw pressure data
    press_raw = (press_data[0] << 16) | (press_data[1] << 8) | press_data[2]
    pressure = press_raw / 25600.0  # Convert to hPa
    
    # Convert raw temperature data
    temp_raw = (temp_data[0] << 16) | (temp_data[1] << 8) | temp_data[2]
    temperature = temp_raw / 100.0  # Convert to °C
    
    return temperature, pressure

# Initialize I2C bus and BMP390
with SMBus(0) as bus:  # Use appropriate bus number
    bmp390_init(bus)
    while True:
        temp, press = bmp390_read(bus)
        print(f"Temperature: {temp:.2f} °C, Pressure: {press:.2f} hPa")
        time.sleep(1)