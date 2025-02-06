import time
import wiringpi
import numpy
import spidev
from ClassLCD import LCD
import paho.mqtt.client as mqtt

# MQTT settings
MQTT_HOST ="mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL =60
MQTT_TOPIC = "channels/2821967/publish"
MQTT_CLIENT_ID = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_USER = "CRQYKw0jAAEKNRITDzouFTI"
MQTT_PWD = "+cm5H5ON/XwqDbHqx0puzrUG"

# Functions
# Activate LCD using CS
def ActivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 0)
    time.sleep(0.000005)

# Deactivate LCD using CS
def DeactivateLCD():
    wiringpi.digitalWrite(pin_CS_lcd, 1)
    time.sleep(0.000005)

# Call back functions (reaction to events during operation)
def on_connect(client, userdata, flags, rc):
    if rc==0:
        print("Connected OK with result code "+str(rc))
    else:
        print("Bad connection with result code "+str(rc))
 
def on_disconnect(client, userdata, flags, rc=0):
    print("Disconnected result code "+str(rc))
 
def on_message(client,userdata,msg):
    print("Received a message on topic: " + msg.topic + "; message: " + msg.payload)

# Set up a MQTT Client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
 
# Connect callback handlers to client
client.on_connect= on_connect
client.on_disconnect= on_disconnect
client.on_message= on_message
 
print("Attempting to connect to %s" % MQTT_HOST)
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start() #start the loop

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
pin_led = 2
pin_switch0 = 3
pin_switch1 = 4
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
        MQTT_DATA = "field1="+str(dutycycle)+"&status=MQTTPUBLISH"
        print(MQTT_DATA)
        try:
            client.publish(topic=MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False, properties=None)
            time.sleep(0.5)
        except OSError:
            client.reconnect()
except KeyboardInterrupt:
    wiringpi.softPwmWrite(pin_led, 0)            # stop the white PWM output
    ActivateLCD()
    lcd_1.clear()
    lcd_1.refresh()
    lcd_1.set_backlight(0)
    DeactivateLCD()
    print("\nDone")
