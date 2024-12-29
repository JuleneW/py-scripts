import wiringpi as wp
import time

# Pin configuration for stepper motor coils
PIN_A = 3  # GPIO pin for coil A
PIN_B = 4  # GPIO pin for coil B
PIN_C = 6  # GPIO pin for coil C
PIN_D = 9  # GPIO pin for coil D
pinSwitch = 1

# Stepper motor sequence for wave drive
wave_drive_sequence = [
    [1, 0, 0, 0],  # Step 1: Coil A
    [0, 1, 0, 0],  # Step 2: Coil B
    [0, 0, 1, 0],  # Step 3: Coil C
    [0, 0, 0, 1],  # Step 4: Coil D
]

# Setup
wp.wiringPiSetup()  # Initialize WiringOP
wp.pinMode(PIN_A, 1)
wp.pinMode(PIN_B, 1)
wp.pinMode(PIN_C, 1)
wp.pinMode(PIN_D, 1)
wp.pinMode(pinSwitch, 0)

# Function to perform a single step
def perform_step(step_sequence):
    wp.digitalWrite(PIN_A, step_sequence[0])
    wp.digitalWrite(PIN_B, step_sequence[1])
    wp.digitalWrite(PIN_C, step_sequence[2])
    wp.digitalWrite(PIN_D, step_sequence[3])

# Rotate the motor
while True:
    if wp.digitalRead(pinSwitch) == 1:     # HIGH
        for step in wave_drive_sequence:
            print("Rotating clockwise")
            perform_step(step)
            time.sleep(0.1)                # wait for next step
    else:
        for step in reversed(wave_drive_sequence):
            print("rotating counter-clockwise")
            perform_step(step)
            time.sleep(0.1)