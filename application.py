# IMPORTS
import time, sys
from time import sleep
from flask import *
import I2C_LCD_driver
import RPi.GPIO as GPIO
from datetime import datetime
from RpiMotorLib import RpiMotorLib
from gpiozero import MotionSensor

# USER INPUTS
volume_bottle = vol     # Volume of bottle in litres (l)

# PINS
# I2C LCD SDA 2, SCL 3, ADDRESS 0x27
# Motor Drivers # IN1, IN2, IN3, IN4  **NOTE: Nema 17HS4401 & 17HS6001 wiring are different**
MD1_Pins = [27, 5, 6, 13]        # SM1 Conveyor
MD2_Pins = [12, 16, 20, 21]     # SM2 Rotary
MD3_Pins = [22, 10, 9, 11]      # SM3 Screwing
# Linear Actuator #
LA1_enA = 18    # Linear Actuator Fill
LA1_IN1 = 25
LA1_IN2 = 8
LA2_enB = 15    # Linear Actuator Screw
LA2_IN3 = 7
LA2_IN4 = 1
# Sensors #
sensor_Flow = 26
IR1 = MotionSensor(23)
IR2 = MotionSensor(24)
# Relays #
relay_WaterPump = 19
# SETUP
# I2C LCD
mylcd = I2C_LCD_driver.lcd()
# Water Flow Sensor #
GPIO.setup(sensor_Flow, GPIO.IN, pull_up_down = GPIO.PUD_UP)
global count    # Pulses
global flow     # Litres = Pulses / (60 * 7.5)
count = 0
flow = 0
def countPulse(channel):
    global count, flow
    count = count+1
    flow = count / (60 * 7.5)    
    print(flow)
GPIO.add_event_detect(sensor_Flow, GPIO.FALLING, callback=countPulse)
# Motor Drivers #
def action_rotary():
    MD2_Rotary = RpiMotorLib.BYJMotor("Motor_Rotary", "Nema")   # Name, Motor type
    MD2_Rotary.motor_run(MD2_Pins, #List of motor GPIO pins
                            0.001,    # Time between steps (s), default 0.001
                            13,    # Number of steps
                            False,  # CCW - False, CW - True
                            False,  # True - Print verbose output 
                            "full", # Step type full, half, wave
                            .0)    # Initial delay (s)
    count = 0
    flow = 0
    sleep(3)
def action_screw():
    MD3_Screw = RpiMotorLib.BYJMotor("Motor_Screw", "Nema")     # Name, Motor type
    MD3_Screw.motor_run(MD3_Pins, #List of motor GPIO pins
                            0.001,    # Time between steps (s), default 0.001
                            60,    # Number of steps
                            False,  # CCW - False, CW - True
                            False,  # True - Print verbose output 
                            "full", # Step type full, half, wave
                            .0)    # Initial delay (s)
    count = 0
    flow = 0
    sleep(3)

# Linear Actuators #

# Relay - Water Pump #
GPIO.setup(relay_WaterPump, GPIO.OUT)
GPIO.output(relay_WaterPump, GPIO.HIGH) # HIGH - OFF, LOW - ON
def action_filling():
    global count, flow
    mylcd.lcd_display_string("Fill: %.2f L" % flow, 2) # Water
    GPIO.output(relay_WaterPump, GPIO.LOW) # LOW - ON, HIGH - OFF
    if flow >= volume_bottle:   # Stops when flow reaches volume intented
        count = 0
        flow = 0
        GPIO.output(relay_WaterPump, GPIO.HIGH)
        task1S = 1
        sleep(3)
    
# Additional setup #
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
SYS_FLOW = 2
task = 4

def task1():
    # Filling & Screwing
    action_filling()
    action_screw()
    action_rotary()
def task2():
    # Filling
    action_filling()
    action_rotary()
def task3():
    # Screwing
    action_screw()
    action_rotary()
def task4():
    # Idle
    action_rotary()
    sleep(2)

# LOOP
@app.route("/",methods=['GET','POST'])
def home():
    if request.form['btnState'] == "ON":
        # 0 is HIGH, 1 is LOW
        print(SYS_FLOW)
        sleep(3)
        if SYS_FLOW == 1:
            if (IR1.value != 1 and IR2.value != 1):     # 2
                task1()
                SYS_FLOW = 4    #11
            elif (IR1.value != 0 and IR2.value != 1):     # 3
                task3()
                SYS_FLOW = 3    #01

        if SYS_FLOW == 2:
            if (IR1.value != 0 and IR2.value != 0):
                task4()
                SYS_FLOW = 2
            elif (IR1.value != 1 and IR2.value != 0):   
                task2()
                SYS_FLOW = 1    #10

        if SYS_FLOW == 3:
            if (IR1.value != 1 and IR2.value != 0):   
                task2()
                SYS_FLOW = 1    #10
            elif (IR1.value != 0 and IR2.value != 0):
                task4()
                SYS_FLOW = 2

        if SYS_FLOW == 4:
            if (IR1.value != 1 and IR2.value != 1):     # 2
                task1()
                SYS_FLOW = 4
            if (IR1.value != 0 and IR2.value != 1):     # 3
                task3()
                SYS_FLOW = 3
    else
        task4()
    return render_template("home.html")

if __name__ == "__main__":
    app.run(debug=True)

GPIO.cleanup()
