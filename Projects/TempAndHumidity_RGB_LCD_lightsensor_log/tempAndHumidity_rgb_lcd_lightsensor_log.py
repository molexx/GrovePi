# -*- coding: UTF-8 -*-

# tempAndHumidity_rgb_lcd_lightsensor_log.py
# 
# Reads the temp and humidity, logs them to a file in csv format with timestamp, if the light sensor is triggered show the values
# on the RGB LCD display otherwise the RGB LCD display is blanked (display is in a cupboard)
# 
# Adapted from Advanced_RGB_LCD_TempAndHumidity by DanKline
# 
# 
# Uses from the GrovePi starter kit:
#   RGB LCD Display
#   DHT Sensor
#   light sensor
# 
# 
# Features:
#  display according to user's preference of centigrade, fahrenheit or both
#  pad out the text to fit the RGB display neatly, don't show '.0' at the end of numbers
#  turn off RGB display when there is no light so it's shut in a cupboard
#  append log to file in csv format: timestamp,temperature,humidity
#  dump formatted values to console
#

import decimal
import grovepi
from datetime import *
import math
import sys

sys.path.insert(0, '../../Software/Python/grove_rgb_lcd')  #don't make a copy of the library, use it in place
from grove_rgb_lcd import *


preferredFormat = 'C'   # 'C' 'F' or 'B' for centigrade/fahrenheit/both
dht_sensor_port = 7     # Connect the DHt sensor to port 7
dht_sensor_type = 0     # 
light_sensor_port = 0   # Connect the Grove Light Sensor to analog port A0 - SIG,NC,VCC,GND
greenTemperature = 20.0        # display will be green if this is the temp, in degrees C
logfilePath = "tempHumid.log"  # append to file in csv format: timestamp,temperature,humidity
lightSensorThreshold = 50      # Turn on display once light sensor resistance drops below this value (k)



# Function Definitions
def CtoF( tempc ):
   "This converts celcius to fahrenheit"
   tempf = round((tempc * 1.8) + 32, 2);
   return tempf;

def strStrip(num):
    "convert number to string but remove '.0' from the end"
    s = str(num);
    return(s.rstrip('0').rstrip('.') if '.' in s else s);

def formatTemp(valueInDegreesC):     # return the temperature in the user's preferred format
    "expects global variable 'preferredFormat' to be C or F"
    if (preferredFormat == "F"):
        return strStrip(CtoF(valueInDegreesC)) + "F";
    elif (preferredFormat == "B"):
        return strStrip(valueInDegreesC) + "C/" + strStrip(CtoF(valueInDegreesC)) + "F";
    else:
        #LCD display does not like the degrees symbol   return strStrip(valueInDegreesC) + "°C";
        return strStrip(valueInDegreesC) + "C";

def calcColorAdj(variance):     # Calc the adjustment value of the background color
    "Because there is 6 degrees mapping to 255 values, 42.5 is the factor for 12 degree spread"
    factor = 42.5;
    adj = abs(int(factor * variance));
    if adj > 255:
        adj = 255;
    return adj;

def calcBG(temp):
    "This calculates the color value for the background"
    
    if(temp == greenTemperature):             # perfect, all on green
        bgR = 0;
        bgG = 255;
        bgB = 0;
    else:
        variance = temp - greenTemperature;   # Calculate the variance
        adj = calcColorAdj(variance);   # Scale it to 8 bit int
        
        if(variance < 0):
            bgR = 0;                    # too cold, no red
            bgG = 255 - adj;
            bgB = adj;                  # green and blue slide equally with adj
            
        else:                           #too hot - no blue
            bgR = adj;                  # Red and Green slide equally with Adj
            bgG = 255 - adj;
            bgB = 0;
    
    bgList = [bgR,bgG,bgB]          #build list of color values to return
    #print "calcRGB: temp: " + str(temp) + ", greenTemperature: " + str(greenTemperature) + ", variance: " + str(variance) + ", adj: " + str(adj) + " generates colour: (",bgList[0],",",bgList[1],",",bgList[2],")";   # this was to test and debug color value list
    return bgList;


def getLightSensorResistance():
    sensor_value = grovepi.analogRead(light_sensor_port)
    
    if (not math.isnan(sensor_value)):
        if (sensor_value == 0):
            sensor_value = 1
        
        # Calculate resistance of sensor in K
        resistance = (float)(1023 - sensor_value) * 10 / sensor_value
        return(resistance)
    else:
        print "ERROR: grovepi.analogRead(", light_sensor_port, "): ", sensor_value
        return("ERROR")




print "config: lightSensorThreshold: ",lightSensorThreshold, ", greenTemperature: ", formatTemp(greenTemperature), ", logging to file: ", logfilePath

lastTemp = 0.0001          # initialize a floating point temp variable
lastHum = 0.0001           # initialize a floating Point humidity variable
lcdDisplayIsOn = True      # remember state to prevent needless setting
lcdText = None
bgList = None

grovepi.pinMode(light_sensor_port, "INPUT")

#if logfilePath is set, open it for writing in append mode
if ('logfilePath' in locals()):
    print "opening file '" + logfilePath + "' for writing...";
    logfile = open(logfilePath, 'a');
else:
    print "No logfilePath set.";


while True:
    
    try:
        temp = 0.00001
        hum = 0.00001

        [ temp,hum ] = grovepi.dht(dht_sensor_port, dht_sensor_type)       #Get the temperature and Humidity from the DHT sensor
        lightSensorResistance = getLightSensorResistance()

        print datetime.now(), " temp: ", temp, "raw, ", formatTemp(temp), "\t\t" + "Humidity: ", hum,"%, lightSensorResistance: ", lightSensorResistance
        
        if (lightSensorResistance != "ERROR"):
            if (lightSensorResistance < lightSensorThreshold): 
                if (lcdDisplayIsOn == False):
                    lcdDisplayIsOn = True
                    print "turned on LCD display - lightSensorResistance is ", lightSensorResistance, " so below threshold of ", lightSensorThreshold
                    if (bgList != None and lcdText != None):
                        setRGB(bgList[0],bgList[1],bgList[2])   # parse our list into the color settings
                        setText(lcdText)
            else:
                if (lcdDisplayIsOn == True):
                    #turn off lcd display
                    setText("")
                    setRGB(0,0,0)
                    lcdDisplayIsOn = False
                    print "turned off LCD display - lightSensorResistance is ", lightSensorResistance, " so above threshold of ", lightSensorThreshold
        
        #if values are not IOErrors and have changed        
        if ((temp != lastTemp) or (hum != lastHum)) and not math.isnan(temp) and not math.isnan(hum):
                
                lastHum = hum          # save temp & humidity values so that there is no update to the RGB LCD
                lastTemp = temp        # this reduces the flashing of the display
                
                bgList = calcBG(temp)           # Calculate background colors
                paddedTemp = (formatTemp(temp) + "           ")[:10]    # 16 chars per line
                lcdText = "Temp: " + paddedTemp + "Humidity: " + strStrip(hum) + "%" # update the RGB LCD display
                
                if (lcdDisplayIsOn == True):               
                    setRGB(bgList[0],bgList[1],bgList[2])   # parse our list into the color settings
                    setText(lcdText)
                
                #log values to file if logfile is configured
                if ('logfile' in locals()):
                    logMe = datetime.now().isoformat() + "," + str(temp) + "," + str(hum) + "\n"
                    logfile.write(logMe)
                    logfile.flush()


    except (IOError,TypeError) as e:
        print "Error" + str(e)
    
