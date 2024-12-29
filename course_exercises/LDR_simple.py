import  time 
import wiringpi 
import sys

#SETUP 
print ("Start")
pinLDR = 1
wiringpi.wiringPiSetup() 
wiringpi.pinMode(pinLDR, 0)                       # Set pin to mode 0 ( INPUT )

#infinite loop - stop using CTRL-C 
while True: 
    if(wiringpi.digitalRead(pinLDR) == 0):   #input is active low
        print("dark") 
        time.sleep (0.5)
    else: 
        print ("light")
        time.sleep (0.5)