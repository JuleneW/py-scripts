import time
import wiringpi
import sys

#Make a flashing light of the 4 LEDs (together on, together off) 
#with a waiting time of 0.1 seconds between on and off. 
#Choose which GPIO pins you use for this.

pins = [2, 3, 4, 6]

def blink_all(pins):
    for pin in pins:
        wiringpi.digitalWrite(pin, 1)
    time.sleep(0.1)
    for pin in pins:
        wiringpi.digitalWrite(pin, 0)
    time.sleep(0.1)

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

