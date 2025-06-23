import RPi.GPIO as GPIO
import time
import threading
import sys
import os
import select
import smtplib
import logging
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime

log_file = '/path/to/your/file'
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
	filename=log_file,
	level=logging.INFO,
	format='%(asctime)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()
logging.info('Program Started')

GPIO.setmode(GPIO.BCM)

LED_red_1 = 23
LED_red_2 = 25
LED_green = 24
panic_button = 16
ir_sensor = 12

stop_flag = False
button_triggered = False
ir_alarm_triggered = False
alternate_started = False


GPIO.setup(LED_red_1, GPIO.OUT)
GPIO.setup(LED_red_2, GPIO.OUT)
GPIO.setup(LED_green, GPIO.OUT)
GPIO.setup(ir_sensor, GPIO.IN)
GPIO.setup(panic_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.output(LED_green, GPIO.HIGH)

def all_off():
	GPIO.output(LED_green, GPIO.LOW)
	GPIO.output(LED_red_1, GPIO.LOW)
	GPIO.output(LED_red_2, GPIO.LOW)

    
def alternate(delay=0.5):
    while not stop_flag:
        GPIO.output(LED_red_1, GPIO.HIGH)
        GPIO.output(LED_red_2, GPIO.LOW)
        time.sleep(delay)
        GPIO.output(LED_red_2, GPIO.HIGH)
        GPIO.output(LED_red_1, GPIO.LOW)
        time.sleep(delay)
        GPIO.output(LED_red_1, GPIO.HIGH)
        GPIO.output(LED_red_2, GPIO.HIGH)
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
                print('Stop command recieved!!!!')
                stop_flag = True
            elif cmd == 'reset':
                print('Reset command given and now restarting')
                GPIO.output(LED_red_1, GPIO.LOW)
                GPIO.output(LED_red_2, GPIO.LOW)
                GPIO.output(LED_green, GPIO.LOW)
                time.sleep(0.5)
                GPIO.cleanup()
                os.execv(sys.executable, [sys.executable] + sys.argv)
            
        
def check_button_press():
    global button_triggered
    while not stop_flag and not button_triggered:
        if GPIO.input(panic_button) == GPIO.LOW:
            logging.info('Panic button has been pressed')
            print('Panic Button pressed')
            button_triggered = True
            GPIO.output(LED_green, GPIO.LOW)
        time.sleep(0.1)
        
def check_ir_sensor():
    global ir_alarm_triggered
    while not stop_flag:
        if GPIO.input(ir_sensor) == GPIO.HIGH and not ir_alarm_triggered:
            logging.info('IR Sensor tripped')
            print('FIRE HAS BEEN DETECTED')
            ir_alarm_triggered = True
        time.sleep(0.1)
        
def send_SMS_button(body):
    email_address = os.getenv('Email_Address')
    email_password = os.getenv('Email_Password')
    to_SMS = os.getenv('SMS_Address')

    body = 'EMERGENCY BUTTON PRESSED'
    msg = MIMEText(body)
    msg['From'] = email_address
    msg['To'] = to_SMS
    msg['Subject'] = ''
    try:
        with smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465) as server:
            server.login(email_address, email_password)
            server.send_message(msg)
        print ('Text message sent')
    except:
        print('Failed to send message')

def send_SMS_alarm(body):
    email_address = os.getenv('Email_Address')
    email_password = os.getenv('Email_Password')
    to_SMS = os.getenv('SMS_Address')

    body = 'FIRE DETECTED, IR SENSOR DETECTS HEAT!!!!'
    msg = MIMEText(body)
    msg['From'] = email_address
    msg['To'] = to_SMS
    msg['Subject'] = ''
    try:
        with smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465) as server:
            server.login(email_address, email_password)
            server.send_message(msg)
        print ('Text message sent')
    except:
        print('Failed to send message')
        
        
        
threading.Thread(target=listen_for_commands, daemon=True).start()
threading.Thread(target=check_button_press, daemon=True).start
threading.Thread(target=check_ir_sensor, daemon=True).start()
    
try:
    print('Pressing button will activate ')
    
    while not stop_flag:
        if  button_triggered and not alternate_started:
            print('ALARM HAS BEEN ACTIVATED')
            GPIO.output(LED_green, GPIO.LOW)
            threading.Thread(target=alternate, daemon=True).start()
            alternate_started = True
            send_SMS_button('body')
        elif ir_alarm_triggered and not alternate_started:
            print('FIRE ALARM ACTIVATED')
            GPIO.output(LED_green, GPIO.LOW)
            threading.Thread(target=alternate, daemon=True).start()
            alternate_started = True
            send_SMS_alarm('body')
        time.sleep(0.1)
        
        
except KeyboardInterrupt:
    print('Program is interupted')
    
finally:
	logging.info('Program has stopped')
	all_off()
	GPIO.cleanup()
	print('Program has completed')
