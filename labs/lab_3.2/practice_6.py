import time 
import wiringpi 
import sys

#SETUP 
pinRelay1 = 2
pinRelay2 = 1
pinSwitch = 5
wiringpi.wiringPiSetup() 
wiringpi.pinMode(pinRelay1, 1)                       # Set pin to mode 1 ( OUTPUT )
wiringpi.pinMode(pinRelay2, 1)                       # Set pin to mode 1 ( OUTPUT )
wiringpi.pinMode (pinSwitch, 0)                      # Set pin to mode 0 ( INPUT )

while True:
    if(wiringpi.digitalRead(pinSwitch) == 1):            # input is active high
        wiringpi.digitalWrite(pinRelay1, 1)
        wiringpi.digitalWrite(pinRelay2, 0)
        print("Relay 1 on") 
        time.sleep (0.3)      #anti bouncing      
    else:  
        wiringpi.digitalWrite(pinRelay1, 0)
        wiringpi.digitalWrite(pinRelay2, 1)
        print("Relay 2 on")
        time.sleep (0.3)      #anti bouncing 