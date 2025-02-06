import time
import wiringpi
import numpy
import threading

exit_event = threading.Event()

#Setup
print("Start")
pin_led = 3
pin_switch0 = 0
pin_switch1 = 1
debounce_time = 0.3
interval_time = 0.1
wiringpi.wiringPiSetup() 

# Set pin as a softPWM output
wiringpi.softPwmCreate(pin_led, 0, 100)

# Set pins as a input
wiringpi.pinMode(pin_switch0, 0)
wiringpi.pinMode(pin_switch1, 0)

# Start PWM
dutycycle = 50
wiringpi.softPwmWrite(pin_led, dutycycle)


def task_pwm(name):
    global dutycycle
    while True:
        wiringpi.softPwmWrite(pin_led, dutycycle)
        time.sleep(interval_time)
        if exit_event.is_set():
            break


def task_input(name):
    global dutycycle
    while True:
        if(wiringpi.digitalRead(pin_switch0) == 0): # input is active low
            time.sleep(debounce_time) # anti bouncing
            dutycycle = int(numpy.clip(dutycycle+10, 0, 100))
            print(dutycycle)
        if(wiringpi.digitalRead(pin_switch1) == 0): # input is active low
            time.sleep(debounce_time) # anti bouncing
            dutycycle = int(numpy.clip(dutycycle-10, 0, 100))
            print(dutycycle)
        if exit_event.is_set():
            break

#create two new threads
t1 = threading.Thread(target=task_pwm, args=("update pwm",)) # update pwm output every interval_time seconds
t2 = threading.Thread(target=task_input, args=("update setting",)) # update setting every pause_time seconds

#start the thread
t1.start()
t2.start()

#init counter
n=0

#main function
try:
    while True: # dummy code in main thread
        n+=1
        print("Main thread: %s" % n)
        time.sleep(1) 
except KeyboardInterrupt:
    exit_event.set()

