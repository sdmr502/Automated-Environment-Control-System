#Dew Point is the temperature at which dew forms.
#Heat Index is an index that combines air temperature and relative humidity in an attempt to determine the human-perceived equivalent temperature.

import time
import datetime
import board
import Adafruit_DHT
import RPi.GPIO as GPIO
import serial, struct, sys, time, json, random
import aqi
import urllib.request, urllib.parse
import mariadb
from meteocalc import Temp, dew_point, heat_index, wind_chill, feels_like


# Connect to MariaDB Platform
try:
    conn = mariadb.connect(
        user="#",
        password="#",
        host="#",
        port=3306,
        database="climatesys"
    )
except mariadb.Error as e:
    print("Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

# Get Cursor
cur = conn.cursor()

GPIO.setmode(GPIO.BCM) # GPIO Numbers instead of board numbers

MAIN_LIGHTING = 17

SIDERIGHT_FAN = 27

SIDELEFT_FAN = 23

SOIL_SENSOR_1 = 21

DHT_SENSOR = Adafruit_DHT.DHT22

INTAKE_DHT_SENSOR = 22 # GPIO 22

OUTTAKE_DHT_SENSOR = 25 # GPIO 25

MAIN_DHT_SENSOR = 16 # GPIO 16

GPIO.setup(MAIN_LIGHTING, GPIO.OUT) # GPIO Assign mode

GPIO.setup(SIDERIGHT_FAN, GPIO.OUT) # GPIO Assign mode

GPIO.setup(SIDELEFT_FAN, GPIO.OUT) # GPIO Assign mode

GPIO.setup(SOIL_SENSOR_1, GPIO.IN)
     
def countdown(t):
    while t > 0:
        t -= 1
        time.sleep(1)
   
def is_between(time, time_range):
    if time_range[1] < time_range[0]:
        return time >= time_range[0] or time <= time_range[1]
    return time_range[0] <= time <= time_range[1]

def setRelay(pin,action, boot = 1):
    if action == "start" and GPIO.input(pin) == 0:
        GPIO.output(pin, GPIO.HIGH) # on
        print("\033[1;32;40m" ,pin ,"set to on \n")
    elif action == "stop" and GPIO.input(pin):
        GPIO.output(pin, GPIO.LOW) # out
        print("\033[1;31;40m" ,pin ,"set to off \n")
    else:
        print("\033[1;33;40m" ,pin, " is already set to required value. \n  Hardware Value:", GPIO.input(pin) , "\n")

def checkOutput(pin):
    output = GPIO.input(pin) # on
    return output
    
def checkMoisture(channel):
    if GPIO.input(channel):
        return 0
    else:
        return 1

def cleanAirCycle():
    sch = [5]
    if int(time.strftime('%M')) in sch:
        print("Starting Clean Air Cycle...")
        setRelay(SIDERIGHT_FAN, "start")
        countdown(15)
        setRelay(SIDELEFT_FAN, "start")
        countdown(30)
        setRelay(SIDERIGHT_FAN, "stop")
        countdown(60)
        setRelay(SIDERIGHT_FAN, "start")
        countdown(5)
        setRelay(SIDERIGHT_FAN, "stop")
        countdown(10)
        setRelay(SIDERIGHT_FAN, "start")
        countdown(15)
        setRelay(SIDERIGHT_FAN, "stop")
        setRelay(SIDELEFT_FAN, "stop")

def getThreshold(percentage, of):
    return int(((percentage * of) / 100))

def returnThreshold(threshold, target, operator):
    if operator == '-':
        return (target - threshold)
    elif operator == '+':
        return (target + threshold)

def withinThreshold(threshold, target, actual):
    if actual is not None:
        if ((target - threshold) <= actual <= (target + threshold)):
            return int(1)
        return int(0)

def setDHTEnvironmentData(sensorPin, sensorType,):
    humidity, temperature_c = Adafruit_DHT.read_retry(sensorType, sensorPin)
    if(temperature_c is not None and -20 <= temperature_c <= 100 and humidity is not None and 0 <= humidity <= 100):
        humidity = round(humidity,2)
        temperature_c = round(temperature_c,2)
        temp_c_meteocalc = Temp(temperature_c, 'c')
        sensorData = {
                "temp": temperature_c,
                "humidity": humidity,
                "dewPoint" : round(dew_point(temperature=temp_c_meteocalc, humidity=humidity).c, 2),
                "heatIndex" : round(heat_index(temperature=temp_c_meteocalc, humidity=humidity).c, 2),
                "sensorData": 1
                }
    else:
        sensorData = {
                "sensorData": 0
                }
    return sensorData

def concat(a, b):
    return (f"{a}{b}")

def numConcat(num1, num2): 
     # find number of digits in num2 
     digits = len(str(num2)) 
     # add zeroes to the end of num1 
     num1 = num1 * (10**digits) 
     # add num2 to num1 
     num1 += num2 
  
     return num1 
def balancer(actual,targetMin, targetMax):
    #The function allows us to simplify the results to determine the best method more dynamically
    if(targetMin <= actual <= targetMax):
        return 1
    elif(actual > targetMin and actual > targetMax):
        return 2
    elif(actual < targetMin and actual < targetMax):
        return 3
    elif(targetMin > actual):
        return 2
    elif(targetMax < actual):
        return 4
    else:
        return 0        
#def correctBalance(option):
    #we are going to ignore the first digit in our option.
    
    
    

TARGET_TEMP = 27
TARGET_HU = 47

TEMPERATURE_THRESHOLD_PERCENTAGE = 15
HUMIDITY_THRESHOLD_PERCENTAGE = 5



        
environment = {
    "thresholds":{},
    "moist": checkMoisture(SOIL_SENSOR_1),
    "intake": {},
    "outtake": {},
    "room": {},
    "outputs" : {
        "lighting": {'status' : 0},
        "intakeFan": {'status' : 0},
        "outtakeFan": {'status' : 0}, 
        }
    }

while True:
    try:
        timestamp = time.strftime('%H:%M')
        localtime = time.asctime( time.localtime(time.time()) )
        print("\033[1;36;40m Local current time :", localtime ,"\n")
        
        if(is_between(timestamp, ("08:00", "01:59"))):
            print("\033[1;33;40m Light should be set ON \n")
            setRelay(MAIN_LIGHTING, "start")
        else:
            print("\033[1;34;40m Light should be set OFF \n")
            setRelay(MAIN_LIGHTING, "stop")
            cleanAirCycle()
            
        
        cur.execute("SELECT AVG(mainDewPoint) FROM env WHERE timestamp > NOW() - INTERVAL 48 HOUR")
        riskDewPoint = cur.fetchone()
        
        
        environment["thresholds"] = {
            "temp": getThreshold(TEMPERATURE_THRESHOLD_PERCENTAGE, TARGET_TEMP),
            "humidity": getThreshold(HUMIDITY_THRESHOLD_PERCENTAGE, TARGET_HU),
            "riskDewPoint": round(float(riskDewPoint[0]),2)
            }
        environment["thresholds"]['triggers'] = {
            "tempMin": returnThreshold(environment["thresholds"]['temp'], TARGET_TEMP, '-'),
            "tempMax": returnThreshold(environment["thresholds"]['temp'], TARGET_TEMP, '+'),
            "humidityMin": returnThreshold(environment["thresholds"]['humidity'], TARGET_HU, '-'),
            "humidityMax": returnThreshold(environment["thresholds"]['humidity'], TARGET_HU, '+'),
            }
        
        environment["room"] = setDHTEnvironmentData(MAIN_DHT_SENSOR, DHT_SENSOR)
        environment["intake"] = setDHTEnvironmentData(INTAKE_DHT_SENSOR, DHT_SENSOR)
        environment["outtake"] = setDHTEnvironmentData(OUTTAKE_DHT_SENSOR, DHT_SENSOR)
        
        environment["outputs"]["lighting"]["status"] = checkOutput(MAIN_LIGHTING)
        environment["outputs"]["intakeFan"]["status"] = checkOutput(SIDELEFT_FAN)
        environment["outputs"]["outtakeFan"]["status"]  = checkOutput(SIDERIGHT_FAN)
   
        if(environment["room"]['sensorData'] and environment["intake"]['sensorData'] and environment["outtake"]['sensorData']):
            checkTemperatureThreshold = withinThreshold(environment["thresholds"]['temp'], TARGET_TEMP, environment["room"]['temp'])
            checkHumidityThreshold = withinThreshold(environment["thresholds"]['humidity'], TARGET_HU, environment["room"]['humidity'])
        
            print(environment)
            balancerTemp = balancer(environment["room"]['temp'],environment["thresholds"]['triggers']['tempMin'], environment["thresholds"]['triggers']['tempMax'])
            balancerHumid = balancer(environment["room"]['humidity'],environment["thresholds"]['triggers']['humidityMin'], environment["thresholds"]['triggers']['humidityMax'])
            balancerIntakeTemp = balancer(environment["intake"]['temp'],environment["thresholds"]['triggers']['tempMin'], environment["thresholds"]['triggers']['tempMax'])
            balancerIntakeHumid = balancer(environment["intake"]['humidity'],environment["thresholds"]['triggers']['humidityMin'], environment["thresholds"]['triggers']['humidityMax'])
            balancerOuttakeTemp = balancer(environment["outtake"]['temp'],environment["thresholds"]['triggers']['tempMin'], environment["thresholds"]['triggers']['tempMax'])
            balancerOuttakeHumid = balancer(environment["outtake"]['humidity'],environment["thresholds"]['triggers']['humidityMin'], environment["thresholds"]['triggers']['humidityMax'])
            
            globalBalancer = numConcat(balancerTemp,numConcat(balancerHumid,numConcat(balancerIntakeTemp,numConcat(balancerIntakeHumid,numConcat(balancerOuttakeTemp,balancerOuttakeHumid)))))
            
            if checkTemperatureThreshold and checkHumidityThreshold:
                print("Relax Everything is Good :)")
                option = numConcat(1,globalBalancer)
                setRelay(SIDERIGHT_FAN, "stop")
                setRelay(SIDELEFT_FAN, "stop")
            elif (checkHumidityThreshold is 0 and checkTemperatureThreshold):
                option = numConcat(2,globalBalancer)
                setRelay(SIDERIGHT_FAN, "start")
                setRelay(SIDELEFT_FAN, "stop")
                print("Humidity Correction Required")
            elif (checkHumidityThreshold and checkTemperatureThreshold is 0):
                option = numConcat(3,globalBalancer)
                print("Temperature Correction Required")
                setRelay(SIDERIGHT_FAN, "stop")
                setRelay(SIDELEFT_FAN, "start")
            else:
                option = numConcat(4,globalBalancer)
                print("Enviroment Unstable")
                setRelay(SIDERIGHT_FAN, "start")
                setRelay(SIDELEFT_FAN, "start")
            cur.execute(
                "INSERT INTO env (action,mainTemp,mainHum,mainDewPoint,mainHeatIndex,intakeTemp,intakeHum,intakeDewPoint,intakeHeatIndex,outtakeTemp,outtakeHum,outtakeDewPoint,outtakeHeatIndex,MoistureSensor1,mainLight,intakeFan,outtakeFan,option,targetTemp,targetHum,tempThreshold,humThreshold,tempMax,tempMin,humMax,humMin) VALUES (?, ?, ? ,? ,? ,? ,? ,? ,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("self", environment["room"]['temp'], environment["room"]['humidity'], environment["room"]['dewPoint'], environment["room"]['heatIndex'],
                            environment["intake"]['temp'], environment["intake"]['humidity'], environment["intake"]['dewPoint'], environment["intake"]['heatIndex'],
                            environment["outtake"]['temp'], environment["outtake"]['humidity'], environment["outtake"]['dewPoint'], environment["outtake"]['heatIndex'],
                            environment["moist"],
                            environment["outputs"]["lighting"]["status"], environment["outputs"]["intakeFan"]["status"], environment["outputs"]["outtakeFan"]["status"],
                            option, TARGET_TEMP, TARGET_HU, environment["thresholds"]["temp"], environment["thresholds"]["humidity"],
                            environment["thresholds"]['triggers']["tempMax"],environment["thresholds"]['triggers']["tempMin"],environment["thresholds"]['triggers']["humidityMax"],environment["thresholds"]['triggers']["humidityMin"]     
                 ))
        
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("exiting...")

    time.sleep(1.0)


