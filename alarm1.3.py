import RPi.GPIO as GPIO
import time
from datetime import datetime
import threading
import sys
import os
import select
import smtplib
import logging
import signal
import random
from email.mime.text import MIMEText
from dotenv import load_dotenv

def log_event(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
load_dotenv()

log_file = '/home/publius/fireAlarm/log.txt'
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

LED_red_1 = 23
LED_red_2 = 25
LED_green = 24
panic_button = 16
ir_sensor = 12

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_red_1, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED_red_2, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED_green, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(ir_sensor, GPIO.IN)
    GPIO.setup(panic_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
except Exception as e:
    log_event(f"GPIO setup error: {e}")



logging.info('Program Started')
last_status_date = datetime.now().date()

gpio_initialized = False
last_status_date = None
stop_flag = False
button_triggered = False
ir_alarm_triggered = False
alternate_started = False
today = datetime.now().date()

def setup_gpio():
  global gpio_initialized
  GPIO.setmode(GPIO.BCM)
  gpio_initialized = True

def all_off():
  if gpio_initialized:
    GPIO.output(LED_green, GPIO.LOW)
    GPIO.output(LED_red_1, GPIO.LOW)
    GPIO.output(LED_red_2, GPIO.LOW)
all_off()
GPIO.output(LED_green, GPIO.HIGH)

def handle_exit(signum, frame):
    log_event(f"Shutting down: signal recieved {signum}")
    all_off()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
    
def alternate(delay=0.5):
    while not stop_flag:
        GPIO.output(LED_red_1, GPIO.HIGH)
        GPIO.output(LED_red_2, GPIO.LOW)
        time.sleep(delay)
        GPIO.output(LED_red_2, GPIO.HIGH)
        GPIO.output(LED_red_1, GPIO.LOW)
        time.sleep(delay)
    GPIO.output(LED_red_1, GPIO.LOW)
    GPIO.output(LED_red_2, GPIO.LOW)
    time.sleep(0.1)
        
def listen_for_commands():
    global stop_flag 
    print('Type stop to end the current prorgam or reset to reset it ')
    while not stop_flag:
        if select.select([sys.stdin], [], [], 0.1)[0]:
            cmd = sys.stdin.readline().strip().lower()
            if cmd == 'stop':
                log_event("Stop command recieved")
                stop_flag = True
            elif cmd == 'reset':
                log_event("Reset command recieved")
                time.sleep(0.5)
                GPIO.cleanup()
                os.execv(sys.executable, [sys.executable] + sys.argv)
            
        
def check_button_press():
    global button_triggered, alternate_started
    while not stop_flag and not button_triggered:
        if GPIO.input(panic_button) == GPIO.LOW:
            log_event("Panic button pressed")
            print('Panic Button pressed')
            button_triggered = True
            GPIO.output(LED_green, GPIO.LOW)
        time.sleep(0.1)
        
def check_ir_sensor():
    global ir_alarm_triggered, alternate_started
    while not stop_flag:
        if GPIO.input(ir_sensor) == GPIO.HIGH and not ir_alarm_triggered:
            logging.info('IR Sensor tripped')
            log_event("IR Sensor tripped")
            print('FIRE HAS BEEN DETECTED')
            ir_alarm_triggered = True
        time.sleep(0.1)
        
def send_SMS(body):
    email_address = os.getenv('Email_Address')
    email_password = os.getenv('Email_Password')
    to_SMS = os.getenv('SMS_Address')

    msg = MIMEText(body)
    msg['From'] = email_address
    msg['To'] = to_SMS
    msg['Subject'] = ''
    try:
        with smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465) as server:
            server.login(email_address, email_password)
            server.send_message(msg)
        log_event('Text message sent')
    except:
        log_event("Failed to send message")

threading.Thread(target=listen_for_commands, daemon=True).start()
threading.Thread(target=check_button_press, daemon=True).start()
threading.Thread(target=check_ir_sensor, daemon=True).start()
    
try:
    print('Pressing button will activate ')
    
    while not stop_flag:
        now = datetime.now()
        today = datetime.now().date()
        if now.hour == 6 and last_status_date != today:
       # if last_status_date != today: #test only
            send_SMS('Alarm system is ok, Daily reset sucseeful.')
            log_event("Daily status check sent")
            last_status_date = today

        if  button_triggered and not alternate_started:
            print('ALARM HAS BEEN ACTIVATED')
            GPIO.output(LED_green, GPIO.LOW)
            threading.Thread(target=alternate, daemon=True).start()
            alternate_started = True
            send_SMS('EMERGNCY BUTTON PRESSED')
            button_triggered = False

        elif ir_alarm_triggered and not alternate_started:
            print('FIRE ALARM ACTIVATED')
            GPIO.output(LED_green, GPIO.LOW)
            threading.Thread(target=alternate, daemon=True).start()
            alternate_started = True
            send_SMS('FIRE ALARM ACTIVATE')
            ir_alarm_triggered = False
        time.sleep(0.1)
        
        
except KeyboardInterrupt:
    print('Program is interupted')
    log_event("Program is interupted")
    
finally:
    log_event("Program has stopped")
    all_off()
    GPIO.cleanup()
    print('Program has completed')
    log_event("Program has completed")

