import time
import wiringpi
import sys

#Create an SOS signal on output GPIO1. (1 short pulse, 1 long pulse, 1 short pulse) and repeat this continuous.
#Short pulse = 0.5 s  ---
#Long pulse = 1.5 s   ___ ___ ___

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


print("Start")
wiringpi.wiringPiSetup()
pin = 2
#pin3 = 3   #MAKE SURE ALL LEDS ARE OFF FIRST
#pin4 = 4
#pin6 = 6
#pins = [pin,pin3,pin4,pin6]
#for pin in pins:
    #wiringpi.pinMode(pin, 0)
wiringpi.pinMode(pin, 1)

for i in range(0, 1):
    blink(pin)
print("Done")

