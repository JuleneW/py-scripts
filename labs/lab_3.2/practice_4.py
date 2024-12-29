import time
import wiringpi
import sys

#Create an SOS signal on output GPIO1. (1 short pulse, 1 long pulse, 1 short pulse) and repeat this continuous.
#Short pulse = 0.5 s  ---
#Long pulse = 1.5 s   ___ ___ ___
#Stop this when input GPIO2 is active.

def blink(_pin):
    for i in range(0, 3):
        wiringpi.digitalWrite(_pin, 1)
        time.sleep(0.3)
        wiringpi.digitalWrite(_pin, 0)
        time.sleep(0.3)
    for j in range(0, 3):
        wiringpi.digitalWrite(_pin, 1)
        time.sleep(1.5)
        wiringpi.digitalWrite(_pin, 0)
        time.sleep(0.3)
    for k in range(0, 3):
        wiringpi.digitalWrite(_pin, 1)
        time.sleep(0.3)
        wiringpi.digitalWrite(_pin, 0)
        time.sleep(0.3)


wiringpi.wiringPiSetup()
ledPin = 2
switchPin = 1
wiringpi.pinMode(ledPin, 1)
wiringpi.pinMode(switchPin, 0)

while True:
    if(wiringpi.digitalRead(switchPin) == 1):   #input is active high
        print("LED blinks") 
        time.sleep (0.3)      #anti bouncing 
        blink(ledPin)        
    else: 
        print ("LED not flashing")
        time.sleep (0.3)      #anti bouncing 
        wiringpi.digitalWrite(ledPin, 0)            #Write 0 ( LOW ) to LED 
