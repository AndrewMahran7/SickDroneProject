import time
import math

# Optional gimbal control - only used if running on Raspberry Pi with connected gimbal
# Flight control works completely independently via TCP connection to flight controller
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    
    pwm_pin = 17 # GPIO pin for PWM signal (only used on Raspberry Pi for gimbal)
    frequency = 50 # Frequency in Hz
    duty_cycle = 7.5 # Duty cycle for neutral position (0-100%)

    GPIO.setmode(GPIO.BCM)  # Use physical pin numbering
    GPIO.setup(pwm_pin, GPIO.OUT)  # Set pin as output
    pwm = GPIO.PWM(pwm_pin, frequency)  # Create PWM instance
    pwm.start(duty_cycle)  # Start PWM with initial duty cycle
except ImportError:
    # Running on Windows/other OS - gimbal control disabled, flight control unaffected
    print("RPi.GPIO not available - gimbal control disabled (flight control unaffected)")
    GPIO_AVAILABLE = False
    pwm = None
except Exception as e:
    print(f"GPIO setup failed: {e} - gimbal control disabled (flight control unaffected)")
    GPIO_AVAILABLE = False
    pwm = None

def set_gimbal_angle(angle):
    """
    Set gimbal angle - optional feature for camera control
    Uses GPIO if available (Raspberry Pi), otherwise logs simulation
    Flight control is completely independent of this function
    """
    if GPIO_AVAILABLE and pwm:
        dc = (-2/3) * angle + 120
        pwm.ChangeDutyCycle(dc / 10)
        print(f"Gimbal angle set to {angle} degrees (GPIO control)")
    else:
        print(f"Gimbal simulation: angle set to {angle} degrees (no GPIO available)")

def get_angle(elevation, pos_drone, pos_user):
    """Calculate gimbal angle based on positions - pure math function"""
    dx, dy = pos_user[0] - pos_drone[0], pos_user[1] - pos_drone[1]
    x = math.sqrt(dx**2 + dy**2)
    h = elevation
    angle = (180 / 3.14159) * math.atan2(h, x)  # Convert radians to degrees
    return angle

def center_camera():
    """Center the gimbal camera - optional feature, doesn't affect flight"""
    print("Centering gimbal (optional feature)...")
    set_gimbal_angle(0)  # Center the gimbal
