import  time 
import wiringpi 
import sys

pinTrg = 16
pinEcho = 13

wiringpi.wiringPiSetup()

wiringpi.pinMode(pinTrg, 1)                       # Set pin to mode 1 ( OUTPUT )
wiringpi.pinMode(pinEcho, 0)                      # Set pin to mode 0 ( INPUT )

print('Start')
while True:
    wiringpi.digitalWrite(pinTrg, 1)              # output high
    time.sleep (0.00001)
    wiringpi.digitalWrite(pinTrg, 0)              # output low

    while wiringpi.digitalRead(pinEcho) == 0:
        pass
    signal_high = time.time()
    while wiringpi.digitalRead(pinEcho) == 1:
        pass
    signal_low = time.time()

    time_passed = signal_low - signal_high

    distance = time_passed * 17000

    print('Measured Distance =', round(distance, 1), 'cm')
    time.sleep(15)