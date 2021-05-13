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
        host="localhost",
        port=3306,
        database="climatesys"

    )
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
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
    if int(time.strftime('%M')) == 25:
        print("Starting Clean Air Cycle...")
        setRelay(SIDERIGHT_FAN, "start")
        countdown(5)
        setRelay(SIDELEFT_FAN, "start")
        countdown(5)
        setRelay(SIDERIGHT_FAN, "stop")
        countdown(10)
        setRelay(SIDERIGHT_FAN, "start")
        countdown(5)
        setRelay(SIDELEFT_FAN, "start")
        countdown(5)
        setRelay(SIDERIGHT_FAN, "stop")
        countdown(10)
        setRelay(SIDERIGHT_FAN, "start")
        countdown(30)
        setRelay(SIDERIGHT_FAN, "stop")
        setRelay(SIDELEFT_FAN, "stop")


countdown(5)


TARGET_TEMP = 18
TARGETMAX_TEMP = 27
TARGET_HU = 50
TARGETMAX_HU = 70
#Temp overules Humidity - Theory
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
        
        #Degree Below Target to maintain consistancy on cooling
        OPERATING_START_TRIGGER_TEMP = TARGETMAX_TEMP - 2
        OPERATING_STOP_TRIGGER_TEMP = TARGET_TEMP + 6

        OPERATING_START_TRIGGER_HUM = TARGET_HU + 2
        OPERATING_STOP_TRIGGER_HUM = TARGETMAX_HU - 10

        print("\033[1;31;40m Enviroment Start Temp Trigger: " , OPERATING_START_TRIGGER_TEMP , "C \n")

        print("\033[1;32;40m Enviroment Stop Temp Trigger: " , OPERATING_STOP_TRIGGER_TEMP , "C \n")
      
        print("\033[1;33;40m Enviroment Start Humidity Trigger: " , OPERATING_START_TRIGGER_HUM , "% \n")

        print("\033[1;34;40m Enviroment Stop Humidity Trigger: " , OPERATING_STOP_TRIGGER_HUM , "% \n")
        
        
        
        print("\033[1;32;40m Intake Temp : " , intake_temperature_c , "C \n")
        print("\033[1;32;40m Intake Humidity : " , intake_humidity , "% \n")


        print("\033[1;31;40m Outtake Temp : " , outake_temperature_c , "C \n")
        print("\033[1;31;40m Outtake Humidity : " , outake_humidity , "% \n")
        
        print("\033[1;32;40m Main Temp : " , room_temperature_c , "C \n")
        print("\033[1;32;40m Main Humidity : " , room_humidity , "% \n")
        
        
        
        if room_temperature_c is None or room_humidity is None or outake_temperature_c is None or outake_humidity is None or intake_temperature_c is None or intake_humidity is None:
            print("One of the DHT's report null data. Continuing")
            continue
        else:
            if room_temperature_c < OPERATING_START_TRIGGER_TEMP and TARGET_HU <= room_humidity <= TARGETMAX_HU:
                print("\033[1;34;40m Currently Temp is", room_temperature_c, "C less than",OPERATING_START_TRIGGER_TEMP," and Humidity is", room_humidity,"% equal or less than", TARGETMAX_HU ,"%  \n") 
                setRelay(SIDERIGHT_FAN, "stop")
                setRelay(SIDELEFT_FAN, "stop")
            elif checkOutput(MAIN_LIGHTING):
            ############################################  
                if (OPERATING_START_TRIGGER_HUM <= room_humidity <= OPERATING_STOP_TRIGGER_HUM) == 0 and intake_humidity >= room_humidity and room_humidity > OPERATING_START_TRIGGER_HUM and room_humidity < OPERATING_STOP_TRIGGER_HUM:
                    print("\033[1;34;40m Control Humidity if outake is equal or less than room humidity with Light On \n")
                    setRelay(SIDERIGHT_FAN, "start")
                    setRelay(SIDELEFT_FAN, "stop")
                    countdown(30)
                elif (OPERATING_START_TRIGGER_HUM <= room_humidity <= OPERATING_STOP_TRIGGER_HUM) == 0 and intake_humidity >= room_humidity and OPERATING_START_TRIGGER_HUM > room_humidity  and room_humidity < OPERATING_STOP_TRIGGER_HUM:
                    print("\033[1;34;40m Control Humidity and ensure it's less than Operating Stop Trigger \n") 
                    setRelay(SIDERIGHT_FAN, "stop")
                    setRelay(SIDELEFT_FAN, "stop")
                    countdown(30)    
                elif intake_temperature_c < room_temperature_c and room_temperature_c > OPERATING_START_TRIGGER_TEMP:
                    print("\033[1;34;40m Control Temp => Decrease temp if intake temp is less then main temp and main temp is more then start trigger\n")
                    if(room_temperature_c > outake_temperature_c):
                        setRelay(SIDERIGHT_FAN, "start")
                        setRelay(SIDELEFT_FAN, "start")
                    else:
                        setRelay(SIDELEFT_FAN, "start")
                        setRelay(SIDERIGHT_FAN, "stop")
                  
                elif (TARGET_TEMP <= room_temperature_c <= OPERATING_START_TRIGGER_TEMP) and (OPERATING_START_TRIGGER_HUM <= room_humidity <= OPERATING_STOP_TRIGGER_HUM):
                    setRelay(SIDERIGHT_FAN, "stop")
                    setRelay(SIDELEFT_FAN, "stop")
                else:
                    setRelay(SIDELEFT_FAN, "stop")
                    setRelay(SIDERIGHT_FAN, "stop")
            ##############################################
            elif checkOutput(MAIN_LIGHTING) == 0:
                if (TARGET_TEMP <= room_temperature_c <= OPERATING_START_TRIGGER_TEMP) and (OPERATING_START_TRIGGER_HUM <= room_humidity <= OPERATING_STOP_TRIGGER_HUM):
                    setRelay(SIDERIGHT_FAN, "stop")
                    setRelay(SIDELEFT_FAN, "stop")
                elif intake_temperature_c > room_temperature_c and room_temperature_c < OPERATING_STOP_TRIGGER_TEMP:
                    print("\033[1;34;40m Control Temp => Decrease temp if intake temp is less then main temp and main temp is more then start trigger\n")
                    if(room_temperature_c > outake_temperature_c):
                        setRelay(SIDERIGHT_FAN, "stop")
                        setRelay(SIDELEFT_FAN, "start")
                    else:
                        setRelay(SIDELEFT_FAN, "start")
                        setRelay(SIDERIGHT_FAN, "stop")
                elif intake_temperature_c < room_temperature_c and room_temperature_c > OPERATING_START_TRIGGER_TEMP:
                    setRelay(SIDELEFT_FAN, "stop")
                    setRelay(SIDERIGHT_FAN, "start")

                  
        cur.execute(
            "INSERT INTO env (action,mainTemp,mainHum,intakeTemp,intakeHum,outakeTemp,outtakeHum,MoistureSensor1, mainLight, intakeFan, outtakeFan) VALUES (?, ?, ? ,? ,? ,? ,? ,? ,?, ?, ?)",
            ("monitor", room_temperature_c,room_humidity,intake_temperature_c,intake_humidity,outake_temperature_c,outake_humidity,checkSoilMoisture(SOIL_SENSOR_1), checkOutput(MAIN_LIGHTING),checkOutput(SIDELEFT_FAN),checkOutput(SIDERIGHT_FAN)))

        if(is_between(timestamp, ("00:00", "18:00"))):
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


