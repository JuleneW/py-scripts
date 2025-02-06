import time
import wiringpi
import numpy
import spidev
from ClassLCD import LCD

def ActivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 0)       # Actived LCD using CS
    time.sleep(0.000005)

def DeactivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 1)       # Deactived LCD using CS
    time.sleep(0.000005)

PIN_OUT     =   {  
                'SCLK'  :   14,
                'DIN'   :   11,
                'DC'    :   9, 
                'CS'    :   15,
                'RST'   :   10,
                'LED'   :   6, #backlight   
}

#Setup
print("Start")
pin_led = 3
pin_switch0 = 0
pin_switch1 = 1
pin_CS_lcd = 15
debounce_time = 0.3

wiringpi.wiringPiSetup() 
#(channel, port, speed, mode)
wiringpi.wiringPiSPISetupMode(1, 0, 400000, 0)
# Set pin as a softPWM output
wiringpi.softPwmCreate(pin_led, 0, 100)

# Set pins as a input
wiringpi.pinMode(pin_switch0, 0)
wiringpi.pinMode(pin_switch1, 0)

# Set pin to mode 1 ( OUTPUT )
wiringpi.pinMode(pin_CS_lcd , 1)

# Start PWM
dutycycle = 50
wiringpi.softPwmWrite(pin_led, dutycycle)

ActivateLCD()
lcd_1 = LCD(PIN_OUT)

try:
    lcd_1.clear()
    lcd_1.set_backlight(1)
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
        ActivateLCD()
        lcd_1.clear()
        lcd_1.go_to_xy(0, 0)
        lcd_1.put_string('Lights:' + str(dutycycle) + '%')
        lcd_1.refresh()
        DeactivateLCD()
        time.sleep(0.5)
except KeyboardInterrupt:
    wiringpi.softPwmWrite(pin_led, 0)            # stop the white PWM output
    ActivateLCD()
    lcd_1.clear()
    lcd_1.refresh()
    lcd_1.set_backlight(0)
    DeactivateLCD()
    print("\nDone")
