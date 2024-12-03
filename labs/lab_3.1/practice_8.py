import time
import wiringpi
import sys

#Fade the 4 LEDs in 4 steps from 25 to 100%. Time between 1 step is 2s.

#pin = 2
pins = [2, 3, 4, 6]
brightness_levels = [100, 75, 50, 25]

def fade(pins, brightness_levels):
    for level in brightness_levels:
        for pin in pins:
            wiringpi.softPwmWrite(pin, level)
        time.sleep(1)

#SETUP
print("Start fading")
wiringpi.wiringPiSetup()
for pin in pins:
    wiringpi.softPwmCreate(pin, 0, 100)

#MAIN
for i in range(0,1):
    fade(pins, brightness_levels)

#cleanup
for pin in pins:
    wiringpi.softPwmWrite(pin, 0)
print("Done")