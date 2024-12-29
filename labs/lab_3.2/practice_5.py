import time
import wiringpi
import sys
#Create a bi-directional running light with the 4 LEDs of the LED bar. 
#The running light moves to the left when GPIO2 is activated and 
#the running light moves to the right when GPIO2 is deactivated.
def blink(_pin):
    wiringpi.digitalWrite(_pin, 1)
    time.sleep(0.1)
    wiringpi.digitalWrite(_pin, 0)
    time.sleep(0.1)
#SETUP
led1 = 9
led2 = 6
led3 = 4
led4 = 3
leds = [led1, led2, led3, led4]
switchPin = 1

wiringpi.wiringPiSetup()
for led in leds:
    wiringpi.pinMode(led, 1)
wiringpi.pinMode(switchPin, 0)

#MAIN
while True:
    if(wiringpi.digitalRead(switchPin) == 1):
        for led in reversed(leds):
            blink(led)
    else:
        for led in leds:
            blink(led)
