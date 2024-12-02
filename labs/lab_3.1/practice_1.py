import time
import wiringpi
import sys

def blink(_pin):
    wiringpi.digitalWrite(_pin, 1)
    time.sleep(0.3)
    wiringpi.digitalWrite(_pin, 0)
    time.sleep(0.3)

print("Start")
pin = 2
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin, 1)

while True:
    blink(pin)

