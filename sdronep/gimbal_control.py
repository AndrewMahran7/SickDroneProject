import RPi.GPIO as GPIO
import time
import math

pwm_pin = 17 # GPIO pin for PWM signal
frequency = 50 # Frequency in Hz
duty_cycle = 7.5 # Duty cycle for neutral position (0-100%)

GPIO.setmode(GPIO.BCM)  # Use physical pin numbering
GPIO.setup(pwm_pin, GPIO.OUT)  # Set pin as output
pwm = GPIO.PWM(pwm_pin, frequency)  # Create PWM instance
pwm.start(duty_cycle)  # Start PWM with initial duty cycle

def set_gimbal_angle(angle):
    dc = 2.5 + (angle / 18)
    pwm.ChangeDutyCycle(dc / 10)

def get_angle(elevation, pos_drone, pos_user):
    dx, dy = pos_user[0] - pos_drone[0], pos_user[1] - pos_drone[1]
    x = math.sqrt(dx**2 + dy**2)
    h = elevation
    angle = (180 / 3.14159) * math.atan2(h, x)  # Convert radians to degrees
    return angle

try:
    while True:
        for angle in range(0, 90, 5):  # Sweep from 0 to 90 degrees
            set_gimbal_angle(angle)
            time.sleep(0.01)  # Small delay for smooth movement
        for angle in range(90, 0, -5):  # Sweep from 90 to 0 degrees
            set_gimbal_angle(angle)
            time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    pwm.stop()
    GPIO.cleanup()
