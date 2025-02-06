import time
from smbus2 import SMBus
from bmp280 import BMP280  # Import the BMP280 library

# Initialize I2C bus
bus = SMBus(0)  # Use I2C bus 1 on most Raspberry Pi/Orange Pi boards
address = 0x77

# Initialize the BMP280 sensor
bmp280 = BMP280(i2c_dev=bus, i2c_addr=address)  # Default I2C address (0x76 or 0x77)

while True:
    # Read temperature and pressure
    temperature = bmp280.get_temperature()
    pressure = bmp280.get_pressure()
    sea_level_pressure = 996.1
    altitude = 44330.0 * (1.0 - (pressure / sea_level_pressure) ** (1.0 / 5.255))

    # Display the results
    print("Temperature: {:.2f} °C".format(temperature))
    print("Pressure: {:.2f} hPa".format(pressure))
    print("Altitude: {:.2f} m".format(altitude))

    # Sleep for 3 seconds
    time.sleep(3)