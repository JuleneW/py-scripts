import  time 
import wiringpi 
import sys

def blink(_pin):
    wiringpi.digitalWrite(_pin, 1)
    time.sleep(0.3)
    wiringpi.digitalWrite(_pin, 0)
    time.sleep(0.3)

#SETUP 
pinLed = 2
pinSwitch = 1
wiringpi.wiringPiSetup() 
wiringpi.pinMode(pinLed, 1)                       # Set pin to mode 1 ( OUTPUT )
wiringpi.pinMode (pinSwitch, 0)                 # Set pin to mode 0 ( INPUT )

#infinite loop - stop using CTRL-C 

while True:
    if(wiringpi.digitalRead(pinSwitch) == 1):   #input is active high
        print("LED blinks") 
        time.sleep (0.3)      #anti bouncing 
        blink(pinLed)        
    else: 
        print ("LED not flashing")
        time.sleep (0.3)      #anti bouncing 
        wiringpi.digitalWrite(pinLed, 0)            #Write 0 ( LOW ) to LED 