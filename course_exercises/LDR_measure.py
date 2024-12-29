import  time 
import wiringpi 
import sys

print ("Start")
pinLDR = 1

def measure_charge_time():
    wiringpi.pinMode(pinLDR, 1)                       # Set pin to mode 1 ( OUTPUT )
    wiringpi.digitalWrite(pinLDR, 0)                  # output low
    time.sleep (0.1)

    wiringpi.pinMode(pinLDR, 0)                       # Set pin to mode 0 ( INPUT )
    start = time.time()

    while wiringpi.digitalRead(pinLDR) == 0:          # wait until pin goes HIGH
        pass
        
    stop = time.time()

    interval = stop-start
    print(interval)
    
wiringpi.wiringPiSetup() 
while True:
    measure_charge_time()
    time.sleep(0.5)       #small delay before repeating