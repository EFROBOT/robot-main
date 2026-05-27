import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    class _MockPWM:
        def __init__(self, pin, frequency):
            self.pin = pin
            self.frequency = frequency

        def start(self, duty):
            print(f"PWM start(pin={self.pin}, duty={duty})")

        def ChangeDutyCycle(self, duty):
            print(f"PWM ChangeDutyCycle(pin={self.pin}, duty={duty})")

        def stop(self):
            print(f"PWM stop(pin={self.pin})")

    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"

        def setmode(self, mode):
            print(f"GPIO setmode({mode})")

        def setup(self, pin, mode):
            print(f"GPIO setup(pin={pin}, mode={mode})")

        def PWM(self, pin, frequency):
            return _MockPWM(pin, frequency)

        def cleanup(self):
            print("GPIO cleanup() called")

    GPIO = MockGPIO()

SERVO_PIN = 18
pwm = None

def init_servo():
    global pwm
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)

def set_angle_servo(angle):
    if angle < 0.0: angle = 0.0
    if angle > 180.0: angle = 180.0

    duty_cycle = 2.5 + (10.0 * angle / 180.0)
    pwm.ChangeDutyCycle(duty_cycle)
    
    time.sleep(0.4)
    pwm.ChangeDutyCycle(0) 


if __name__ == '__main__':
    try:
        init_servo()
        
        set_angle_servo(5)
        time.sleep(1)
        
        set_angle_servo(100)
        time.sleep(1)
        
    finally:
        if pwm: 
            pwm.stop()
        GPIO.cleanup()

