import time
import wiringpi
import sys

#Create a bi-directional running light with the 4 LEDs of the LED bar. 
#(From left to right and immediately after from right to left)

def blink(_pin):
    wiringpi.digitalWrite(_pin, 1)
    time.sleep(0.1)
    wiringpi.digitalWrite(_pin, 0)
    time.sleep(0.1)

#SETUP
pin2 = 2
pin3 = 3
pin4 = 4
pin6 = 6
pins = [pin2, pin3, pin4, pin6]
print("Start")
wiringpi.wiringPiSetup()
for pin in pins:
    wiringpi.pinMode(pin, 1)


#MAIN
while True:
    for pin in pins:
        blink(pin)
    for pin in reversed(pins):
        blink(pin)
