import wiringpi
import time

def activate_adc(pin_cs_adc):
    wiringpi.digitalWrite(pin_cs_adc, 0)  # Activate ADC using CS
    time.sleep(0.000005)

def deactivate_adc(pin_cs_adc):
    wiringpi.digitalWrite(pin_cs_adc, 1)  # Deactivate ADC using CS
    time.sleep(0.000005)

def read_adc(adcnum, pin_cs_adc):
    if adcnum < 0 or adcnum > 7:
        return -1
    activate_adc(pin_cs_adc)
    _, recv_data = wiringpi.wiringPiSPIDataRW(1, bytes([1, (8 + adcnum) << 4, 0]))
    deactivate_adc(pin_cs_adc)
    time.sleep(0.000005)
    adcout = ((recv_data[1] & 3) << 8) + recv_data[2]
    return adcout

def update_leds(tmp0, tmp1, threshold, hysteresis_gap, pin_led1, pin_led2, last_state):
    upper_threshold = threshold + hysteresis_gap
    lower_threshold = threshold - hysteresis_gap

    if last_state == "LED1":  # Currently LED1 is ON
        if tmp1 > upper_threshold:  # Switch to LED2 when tmp1 exceeds upper threshold
            wiringpi.digitalWrite(pin_led1, 0)
            wiringpi.digitalWrite(pin_led2, 1)
            return tmp1, "LED2"
        elif tmp0 < lower_threshold:  # Keep LED1 ON if tmp0 drops below lower threshold
            wiringpi.digitalWrite(pin_led1, 1)
            wiringpi.digitalWrite(pin_led2, 0)
            return tmp0, "LED1"

    elif last_state == "LED2":  # Currently LED2 is ON
        if tmp0 > upper_threshold:  # Switch to LED1 when tmp0 exceeds upper threshold
            wiringpi.digitalWrite(pin_led1, 1)
            wiringpi.digitalWrite(pin_led2, 0)
            return tmp0, "LED1"
        elif tmp1 < lower_threshold:  # Keep LED2 ON if tmp1 drops below lower threshold
            wiringpi.digitalWrite(pin_led1, 0)
            wiringpi.digitalWrite(pin_led2, 1)
            return tmp1, "LED2"

    # Default: no change
    return threshold, last_state

# Setup
wiringpi.wiringPiSetup()
pin_cs_adc = 16  # CE pin
pin_led1 = 1  # LED 1
pin_led2 = 2  # LED 2
hysteresis_gap = 10
threshold = 0
last_state = "LED1"  # Start with LED1 ON

# Initialize pins
wiringpi.pinMode(pin_cs_adc, 1)  # Set CE pin to OUTPUT
wiringpi.wiringPiSPISetupMode(1, 0, 500000, 0)  # (channel, port, speed, mode)
wiringpi.pinMode(pin_led1, 1)  # Set LED 1 as OUTPUT
wiringpi.pinMode(pin_led2, 1)  # Set LED 2 as OUTPUT

# Start with LED1 ON
wiringpi.digitalWrite(pin_led1, 1)
wiringpi.digitalWrite(pin_led2, 0)

# Main loop
try:
    while True:
        tmp0 = read_adc(0, pin_cs_adc)  # Read potentiometer 0
        tmp1 = read_adc(1, pin_cs_adc)  # Read potentiometer 1

        print("input0:",tmp0) 
        print("input1:",tmp1)
        #print("threshold:",threshold)
        #print("state:",last_state)
        print()

        # Update LEDs and threshold
        threshold, last_state = update_leds(tmp0, tmp1, threshold, hysteresis_gap, pin_led1, pin_led2, last_state)

        time.sleep(2)

except KeyboardInterrupt:
    wiringpi.digital
