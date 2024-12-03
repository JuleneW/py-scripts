import time
import wiringpi
import sys

#First let LED1 and LED3 go on and off together, 
# then LED2 and LED4 with an interval of 1 second.

led1 = 2
led2 = 3
led3 = 4
led4 = 6

leds = [led1, led2, led3, led4]
uneven_leds = [led1, led3]
even_leds = [led2, led4]

def blink(leds):
    for led in uneven_leds:
        wiringpi.digitalWrite(led, 1)
    time.sleep(0.5)
    for led in uneven_leds:
        wiringpi.digitalWrite(led, 0)
    #time.sleep(0.5)
    for led in even_leds:
        wiringpi.digitalWrite(led, 1)
    time.sleep(0.5)
    for led in even_leds:
        wiringpi.digitalWrite(led, 0)
    #time.sleep(0.5)



#SETUP
print("Start")
wiringpi.wiringPiSetup()
for led in leds:
    wiringpi.pinMode(led, 1)


#MAIN
while True:
    for led in leds:
        blink(led)