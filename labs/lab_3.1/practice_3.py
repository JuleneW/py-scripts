import time
import wiringpi
import sys

#Make a running light in 1 direction with the 4 LEDs of the LED bar. 
#The LEDs turn on and off in sequence from left to right.

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

#while True:
    #blink(pin2)
    #blink(pin3)
    #blink(pin4)
    #blink(pin6)