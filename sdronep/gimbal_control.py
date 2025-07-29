import time
import math

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    
    pwm_pin = 17 # GPIO pin for PWM signal
    frequency = 50 # Frequency in Hz
    duty_cycle = 7.5 # Duty cycle for neutral position (0-100%)

    GPIO.setmode(GPIO.BCM)  # Use physical pin numbering
    GPIO.setup(pwm_pin, GPIO.OUT)  # Set pin as output
    pwm = GPIO.PWM(pwm_pin, frequency)  # Create PWM instance
    pwm.start(duty_cycle)  # Start PWM with initial duty cycle
except ImportError:
    print("RPi.GPIO not available - running in simulation mode")
    GPIO_AVAILABLE = False
    pwm = None
except Exception as e:
    print(f"GPIO setup failed: {e} - running in simulation mode")
    GPIO_AVAILABLE = False
    pwm = None

def set_gimbal_angle(angle):
    """Set gimbal angle - uses GPIO if available, otherwise simulates"""
    if GPIO_AVAILABLE and pwm:
        dc = (-2/3) * angle + 120
        pwm.ChangeDutyCycle(dc / 10)
        print(f"Gimbal angle set to {angle} degrees")
    else:
        print(f"Simulating: Gimbal angle set to {angle} degrees")

def get_angle(elevation, pos_drone, pos_user):
    dx, dy = pos_user[0] - pos_drone[0], pos_user[1] - pos_drone[1]
    x = math.sqrt(dx**2 + dy**2)
    h = elevation
    angle = (180 / 3.14159) * math.atan2(h, x)  # Convert radians to degrees
    return angle

def center_camera():
    """Center the gimbal camera"""
    print("Centering gimbal...")
    set_gimbal_angle(0)  # Center the gimbal
