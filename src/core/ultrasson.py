import RPi.GPIO as GPIO
import time

class Ultrasson:
    def __init__(self, sensor_id, trig, echo, threshold):
        self.sensor_id = sensor_id
        self.trig = trig
        self.echo = echo
        self.threshold = threshold
        
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)

    def get_distance(self):
        GPIO.output(self.trig, True)
        time.sleep(0.00001)
        GPIO.output(self.trig, False)

        pulse_start = time.time()
        pulse_end = time.time()

        timeout = time.time()
        while GPIO.input(self.echo) == 0:
            pulse_start = time.time()
            if pulse_start - timeout > 0.1: return 0

        while GPIO.input(self.echo) == 1:
            pulse_end = time.time()
            if pulse_end - timeout > 0.1: return 0

        duration = pulse_end - pulse_start
        distance = (duration * 34300) / 2
        return round(distance, 2)

    def is_clear(self):
        dist = self.get_distance()
        if dist < self.threshold:
            return False
        return True



#------------------------------------------------------------------------------------
"""import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TRIG = 23
ECHO = 24

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    duration = pulse_end - pulse_start
    # Calcul de la distance (vitesse du son 34300 cm/s)
    distance = (duration * 34300) / 2
    return round(distance, 2)

try:
    while True:
        dist = get_distance()
        print(f"Distance: {dist} cm")
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()"""