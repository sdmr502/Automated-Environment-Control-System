import time
import datetime
import board
import adafruit_dht
import RPi.GPIO as GPIO
import serial, struct, sys, time, json, random
import aqi
import urllib.request, urllib.parse
import mariadb


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

DATA_FILE = 'env/sys.json'

GPIO.setmode(GPIO.BCM) # GPIO Numbers instead of board numbers

MAIN_LIGHTING = 17

SIDERIGHT_FAN = 27

SIDELEFT_FAN = 23

SOIL_SENSOR_1 = 21

INTAKE_DHT_SENSOR = adafruit_dht.DHT22(board.D22) # GPIO 22

OUTTAKE_DHT_SENSOR = adafruit_dht.DHT22(board.D25) # GPIO 25

MAIN_DHT_SENSOR = adafruit_dht.DHT22(board.D16) # GPIO 25

GPIO.setup(MAIN_LIGHTING, GPIO.OUT) # GPIO Assign mode

GPIO.setup(SIDERIGHT_FAN, GPIO.OUT) # GPIO Assign mode

GPIO.setup(SIDELEFT_FAN, GPIO.OUT) # GPIO Assign mode

GPIO.setup(SOIL_SENSOR_1, GPIO.IN)

def sendToDweet(data):
    
    data = json.dumps(data)
    


    post_url = 'https://dweet.io/dweet/for/8yenhS5FAhsmH3Tj'
    headers = {}
    headers['Content-Type'] = 'application/json'
    # POST request encoded data
    json_string = json.dumps(data)
    
    post_data = json_string.encode('ascii')
    #Automatically calls POST method because request has data
    ##post_response = urllib.request.urlopen(url=post_url, data=post_data)
    ##print(post_response.read())

    print("\n Skipped: Randomising next request...")
    ##countdown(random.randint(1,2))
        # open stored data
        

def countdown(t):
    while t > 0:
        t -= 1
        time.sleep(1)

    
def is_between(time, time_range):
    if time_range[1] < time_range[0]:
        return time >= time_range[0] or time <= time_range[1]
    return time_range[0] <= time <= time_range[1]

def setRelay(pin,action, boot = 1):
    if boot == 0:
        data = {
            "type": "output",
            "relay": pin,
            "action": "triggered",
            "command": action,
            "onStart": boot
            }
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
    data = {
            "type": "output",
            "action": "check",
            "pin": pin,
            "result": output
            }
    return output
    
def checkSoilMoisture(channel):

    if GPIO.input(channel):
        return 0
    else:
        return 1
    data = {
        "type": "input",
        "action": "check",
        "pin": channel,
        "result": GPIO.input(channel)
        }
    sendToDweet(data)

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
    

TARGET_TEMP = 27
TARGET_HU = 47

TEMPERATURE_THRESHOLD_PERCENTAGE = 15
HUMIDITY_THRESHOLD_PERCENTAGE = 5

while True:
    try:
        timestamp = time.strftime('%H:%M')
        localtime = time.asctime( time.localtime(time.time()) )
        print("\033[1;36;40m Local current time :", localtime ,"\n")
        
        cleanAirCycle()
        
        # Print the values to the serial port
        room_temperature_c = MAIN_DHT_SENSOR.temperature
        room_humidity = MAIN_DHT_SENSOR.humidity
        
        # Print the values to the serial port
        intake_temperature_c = INTAKE_DHT_SENSOR.temperature
        intake_humidity = INTAKE_DHT_SENSOR.humidity
                
        outake_temperature_c = OUTTAKE_DHT_SENSOR.temperature
        outake_humidity = OUTTAKE_DHT_SENSOR.humidity
        
        #Get the Threshold value 
    
        TEMPERATURE_THRESHOLD = getThreshold(TEMPERATURE_THRESHOLD_PERCENTAGE, TARGET_TEMP)
        HUMIDITY_THRESHOLD = getThreshold(HUMIDITY_THRESHOLD_PERCENTAGE, TARGET_HU)
        
        print("\033[1;31;40m Enviroment  Temperature Threshold: " , TEMPERATURE_THRESHOLD , "C \n")
        print("\033[1;32;40m Enviroment Humidity Threshold: " , HUMIDITY_THRESHOLD , "C \n")
                
        print("\033[1;31;40m Intake Temp : " , intake_temperature_c , "C \n")
        print("\033[1;32;40m Intake Humidity : " , intake_humidity , "% \n")

        print("\033[1;31;40m Outtake Temp : " , outake_temperature_c , "C \n")
        print("\033[1;32;40m Outtake Humidity : " , outake_humidity , "% \n")
        
        print("\033[1;31;40m Main Temp : " , room_temperature_c , "C \n")
        print("\033[1;32;40m Main Humidity : " , room_humidity , "% \n")
        
        
        LIGHTING_STATUS = checkOutput(MAIN_LIGHTING)
        LEFT_FAN_STATUS = checkOutput(SIDELEFT_FAN)
        RIGHT_FAN_STATUS = checkOutput(SIDERIGHT_FAN)
        
        checkTemperatureThreshold = withinThreshold(TEMPERATURE_THRESHOLD, TARGET_TEMP, room_temperature_c)
        checkHumidityThreshold = withinThreshold(HUMIDITY_THRESHOLD, TARGET_HU, room_humidity)
        option = 0

        if room_temperature_c is None or room_humidity is None or outake_temperature_c is None or outake_humidity is None or intake_temperature_c is None or intake_humidity is None:
            print("One of the DHT's report null data. Continuing")
            option = 99
            continue
        else:
            if checkTemperatureThreshold and checkHumidityThreshold:
                option = 1
                setRelay(SIDERIGHT_FAN, "stop")
                setRelay(SIDELEFT_FAN, "stop")
            elif (checkHumidityThreshold == 0):
                print("Humidity Correction Required")
                if(room_humidity < returnThreshold(HUMIDITY_THRESHOLD, TARGET_HU, '-') or outake_humidity > returnThreshold(HUMIDITY_THRESHOLD, TARGET_HU, '-')):
                    if (outake_humidity > returnThreshold(HUMIDITY_THRESHOLD, TARGET_HU, '+')):
                        option = 2
                        if (room_humidity > outake_humidity):
                            option = 3
                            setRelay(SIDERIGHT_FAN, "stop")
                            setRelay(SIDELEFT_FAN, "stop")
                        elif(room_humidity > intake_humidity):
                            option = 21
                            setRelay(SIDERIGHT_FAN, "stop")
                            setRelay(SIDELEFT_FAN, "stop")
                        else:
                            option = 16
                            setRelay(SIDERIGHT_FAN, "stop")
                            setRelay(SIDELEFT_FAN, "stop")

                    else:
                        if(LIGHTING_STATUS):
                            option = 4
                            setRelay(SIDELEFT_FAN, "start")
                            setRelay(SIDERIGHT_FAN, "start")
                        else:
                            option = 5
                            if(outake_humidity > room_humidity):
                                setRelay(SIDELEFT_FAN, "stop")
                                setRelay(SIDERIGHT_FAN, "start")
                            else:
                                setRelay(SIDELEFT_FAN, "stop")
                                setRelay(SIDERIGHT_FAN, "stop")
                else:
                    if(room_temperature_c < returnThreshold(TEMPERATURE_THRESHOLD, TARGET_TEMP, '+')):
                        if(LIGHTING_STATUS):
                            option = 18
                            
                            if (room_temperature_c > outake_temperature_c):
                                option = 8
                                setRelay(SIDELEFT_FAN, "stop")
                                setRelay(SIDERIGHT_FAN, "stop")
                            
                            if(outake_temperature_c > (returnThreshold(TEMPERATURE_THRESHOLD, TARGET_TEMP, '+') + 5)):
                                option = 20
                                setRelay(SIDERIGHT_FAN, "start")
                        else:
                            option = 19
                            setRelay(SIDELEFT_FAN, "stop")
                            setRelay(SIDERIGHT_FAN, "start") 
                    else:
                        option = 17
                        setRelay(SIDELEFT_FAN, "start")
                        setRelay(SIDERIGHT_FAN, "start")
                        countdown(15)
  
            elif (checkTemperatureThreshold == 0 and checkHumidityThreshold):
                 print("Temperature Correction Required")
                 if(room_temperature_c < returnThreshold(TEMPERATURE_THRESHOLD, TARGET_TEMP, '-')):
                    if (intake_temperature_c > room_temperature_c):
                        option = 6
                        if (outake_temperature_c > room_temperature_c):
                            option = 7
                            setRelay(SIDERIGHT_FAN, "start")
                        setRelay(SIDELEFT_FAN, "stop")
                    else:
                        if(LIGHTING_STATUS):
                            if (room_temperature_c > outake_temperature_c):
                                option = 8
                                setRelay(SIDELEFT_FAN, "stop")
                                setRelay(SIDERIGHT_FAN, "stop")
                            else:
                                option = 15
                                setRelay(SIDELEFT_FAN, "stop")
                                setRelay(SIDERIGHT_FAN, "start")
                        else:
                            option = 9
                            setRelay(SIDELEFT_FAN, "stop")
                            setRelay(SIDERIGHT_FAN, "stop")                
            else:
                print("Enviroment Unstable")
                
                
                
                
        cur.execute(
            "INSERT INTO env (action,mainTemp,mainHum,intakeTemp,intakeHum,outakeTemp,outtakeHum,MoistureSensor1, mainLight, intakeFan, outtakeFan, option, targetTemp, targetHum, tempThreshold, humThreshold) VALUES (?, ?, ? ,? ,? ,? ,? ,? ,?, ?, ?, ?, ?, ?, ?, ?)",
            ("monitor", room_temperature_c, room_humidity, intake_temperature_c, intake_humidity, outake_temperature_c, outake_humidity, checkSoilMoisture(SOIL_SENSOR_1), LIGHTING_STATUS, LEFT_FAN_STATUS, RIGHT_FAN_STATUS, option, TARGET_TEMP, TARGET_HU,TEMPERATURE_THRESHOLD, HUMIDITY_THRESHOLD))
        countdown(1)
        if(is_between(timestamp, ("08:00", "01:59"))):
            print("\033[1;33;40m Light should be set ON \n")
            setRelay(MAIN_LIGHTING, "start")
        else:
            print("\033[1;34;40m Light should be set OFF \n")
            setRelay(MAIN_LIGHTING, "stop")
            
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("exiting...")

    time.sleep(1.0)


