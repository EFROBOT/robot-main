import time
import RPi.GPIO as GPIO

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

