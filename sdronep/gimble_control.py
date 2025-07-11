import RPi.GPIO as GPIO
import time

pwm_pin = 11 # GPIO pin for PWM signal
frequency = 50 # Frequency in Hz
duty_cycle = 7.5 # Duty cycle for neutral position (0-100%)

GPIO.setmode(GPIO.BCM)  # Use physical pin numbering
GPIO.setup(pwm_pin, GPIO.OUT)  # Set pin as output
pwm = GPIO.PWM(pwm_pin, frequency)  # Create PWM instance
pwm.start(duty_cycle)  # Start PWM with initial duty cycle

try:
    while True:
        for angle in range(0, 181, 1):  # Sweep from 0 to 180 degrees
            duty_cycle = 2.5 + (angle / 18)  # Convert angle to duty cycle
            pwm.ChangeDutyCycle(duty_cycle)
            time.sleep(0.01)  # Small delay for smooth movement
        for angle in range(180, -1, -1):  # Sweep from 180 to 0 degrees
            duty_cycle = 2.5 + (angle / 18)
            pwm.ChangeDutyCycle(duty_cycle)
            time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    pwm.stop()
    GPIO.cleanup()
    