import time
import wiringpi
import sys

#Create an infinitely long flashing light. 
#Use an LED connected to GPIO (eg. wiringpi pin w2).

def blink(_pin):
    wiringpi.digitalWrite(_pin, 1)
    time.sleep(0.3)
    wiringpi.digitalWrite(_pin, 0)
    time.sleep(0.3)

print("Start")
wiringpi.wiringPiSetup()
pin2 = 2
#pin3 = 3   #MAKE SURE ALL LEDS ARE OFF FIRST
#pin4 = 4
#pin6 = 6
#pins = [pin2,pin3,pin4,pin6]
#for pin in pins:
    #wiringpi.pinMode(pin, 0)
wiringpi.pinMode(pin2, 1)

while True:
    blink(pin2)

