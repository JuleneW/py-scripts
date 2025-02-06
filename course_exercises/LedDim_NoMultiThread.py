import time
import wiringpi
import numpy

#Setup
print("Start")
pin_led = 3
pin_switch0 = 0
pin_switch1 = 1
debounce_time = 0.3
wiringpi.wiringPiSetup() 

# Set pin as a softPWM output
wiringpi.softPwmCreate(pin_led, 0, 100)

# Set pins as a input
wiringpi.pinMode(pin_switch0, 0)
wiringpi.pinMode(pin_switch1, 0)

# Start PWM
dutycycle = 50
wiringpi.softPwmWrite(pin_led, dutycycle)

try:
    while True:
        if(wiringpi.digitalRead(pin_switch0) == 0): # input is active low
            time.sleep(debounce_time) # anti bouncing
            dutycycle = int(numpy.clip(dutycycle+10, 0, 100))
            print(dutycycle)
        if(wiringpi.digitalRead(pin_switch1) == 0): # input is active low
            time.sleep(debounce_time) # anti bouncing
            dutycycle = int(numpy.clip(dutycycle-10, 0, 100))
            print(dutycycle)
        wiringpi.softPwmWrite(pin_led, dutycycle)


except KeyboardInterrupt:
    wiringpi.softPwmWrite(pin_led, 0)            # stop the white PWM output
    print("\nDone")
