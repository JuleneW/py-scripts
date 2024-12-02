import time
import wiringpi
import sys

pins = [2, 3, 4, 6]

def blink_all(pins):
    for pin in pins:
        wiringpi.digitalWrite(pin, 1)
    time.sleep(0.5)
    for pin in pins:
        wiringpi.digitalWrite(pin, 0)
    time.sleep(0.5)

#SETUP
print("Start")
wiringpi.wiringPiSetup()
for pin in pins:
    wiringpi.pinMode(pin, 1)

#MAIN
for i in range(0,10):
    blink_all(pins)

#cleanup
print("Done")

