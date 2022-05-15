#! /usr/bin/env python3
# from logging import Filter

from tkinter import * #the GUI

from tkinter import font as tkFont
from tkinter import ttk
from time import strftime
import tkinter
from matplotlib.backend_bases import LocationEvent
import matplotlib.pyplot as plt
import matplotlib
from pandas.core import frame
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os     #importing os library so as to communicate with the system
from time import sleep  #importing time library to make Rpi wait because its too impatient 

import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
import json
from PIL import Image, ImageTk
#import threading
import logging





##MARK:
os.system ('sudo killall pigpiod') # just to make sure its not already running
os.system ("sudo pigpiod") #Launching GPIO library.  May need to run sudo killall pigpiod" if getting a binding error
sleep(1) # As i said it is too impatient and so if this delay is removed you will get an error
import pigpio #importing GPIO library for PWM.  can also be used for reading the DHT
import adafruit_dht as dht
from board import D2 # pin for temp and humidity

logger = logging.getLogger('root')
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.CRITICAL) #uncomment if you want to disable debug messages


peltierEscMin = 1200
peltierEscMax = 1800
peltierEscMid = 1650
peltierESCPulseWidth = 700
##MARK:
# setup peltierESC
peltierPins = [13,19]
peltierPowerLevel = 0
peltierESC = 13  #Connect the peltierESC in this GPIO pin 
#setup multiple GPIOs because using PWM and Servo on the same will mess each other up
piGPIO = pigpio.pi() 
# piGPIO.hardware_PWM(peltierESC, PWMfreq=20000,PWMduty=1000000)
# piGPIO.set_PWM_dutycycle(peltierESC, 255)
# piGPIO.hardware_PWM(peltierESC, 20000, 0)

piGPIO.set_servo_pulsewidth(peltierESC, peltierEscMin) #for my ESC, this is all it needs to calibrate.  Check your manual.
dhtDevice = dht.DHT22(D2) # only init device once
# setup fridge and humidifier
fridgePin = 17
humidifierPin = 27
isFridgeOn = piGPIO.read(fridgePin) #read the pin state to see if the pin is on or off
isHumidifierOn = piGPIO.read(humidifierPin)#read the pin state to see if the pin is on or off

customPeltierControler = True
hOffset = 0 #used to calibrate humidity sensor
tOffset = 0
##MARK:
filename = '/home/pi/Python/CharcTankOS/CharcTankData.csv'
#filename = 'test.csv'
df = pd.read_csv(filename, index_col=0, parse_dates=True)
writeData = True

if len(df) > 69120: #check to see if there are more than 4 days of data in the list.
    n = len(df) - 69120
    df = df.iloc[n:]


root = Tk() #init tk
root.title("CharcTankOS")

root.geometry("800x480")
##MARK
root.attributes('-fullscreen', True)
root.config(cursor="none")

labelFont = tkFont.nametofont("TkDefaultFont")
labelFont.config(size= 12)
def_font = tkFont.nametofont("TkDefaultFont")
def_font.config(size=15)
bgColor = 'grey7'
fgColor = 'lightgrey'


screenWidth = 800

topBarFrame = Frame(root, height = 65, width = screenWidth, relief = 'raised', borderwidth = 2)
middleFrame = Frame(root, height = 330, width= screenWidth)
bottomBarFrame = Frame(root, height = 65, relief = 'raised', borderwidth = 2)


topBarFrame.pack(side= TOP)
middleFrame.pack(side = TOP)
bottomBarFrame.pack(side = BOTTOM)



#create figure as global var so that we can clear and update live
#for some reason the top and bottom bar add up to 90 lines and 26 lines of padding on the middle frame so set the fig height accordingly
#example "Figure(figsize = (5,3.2), dpi = 100)" will give you a figure that is 320 lines tall + ~26 lines padding for a total of 350
# fig = Figure(figsize = (5,3.22), dpi = 100) 
fig = Figure(figsize = (5,3.2), dpi = 100) 
ax = fig.add_subplot(111)

lf = ttk.Frame(middleFrame)
canvas = FigureCanvasTkAgg(fig, master = lf)
# filteredDF = pd.DataFrame()
graphDF = pd.DataFrame()
graphDFlen = 0
currentTemp = 0
currentRH = 0
averageTemp = 0
averageRH = 0

previousHumidityReading = 0
timerIndex = 0
settingsJSONLocation = 'settings.json'
try:
    with open(settingsJSONLocation, "r") as f:
        settingsJSON = json.load(f) #give settings a default value just in case firebase isnt reachable
        tempHighSet = settingsJSON['tempHighSet']
        tempLowSet = settingsJSON['tempLowSet']
        tempSet = settingsJSON['tempSet']
        midSetpointRH = settingsJSON['rhSet']
        hSetpointRH = settingsJSON['rhHigh']
        lSetpointRH = settingsJSON['rhLow']
        hOffset = settingsJSON['hOffset']
        humidifierOn=settingsJSON['humidifierOn']        
except Exception as e:
        logger.critical('Error opening settings.json')
        logger.critical(e)
#setup firebase, read and set values
try:
    databaseURL = { 'databaseURL' : "https://charctank-default-rtdb.firebaseio.com/"}
    cred = credentials.Certificate("charctank-firebase.json")
    firebase_admin.initialize_app(cred, databaseURL)
    currentDataRef = db.reference("/CurrentData/")
    historyRef = db.reference("/History/")
    settingsRef = db.reference("/Settings/")
    programsRef = db.reference("/Programs/")
except Exception as e:
    logger.critical('Error connecting to Firebase')
    logger.critical(e)

try:
    settingsJSON = settingsRef.get()
    tempHighSet = settingsJSON['tempHighSet']
    tempLowSet = settingsJSON['tempLowSet']
    tempSet = settingsJSON['tempSet']
    midSetpointRH = settingsJSON['rhSet']
    hSetpointRH = settingsJSON['rhHigh']
    lSetpointRH = settingsJSON['rhLow']
    hOffset = settingsJSON['hOffset']
    humidifierOn=settingsJSON['humidifierOn']
except Exception as e:
    logger.critical('Error with settings from Firebase')
    logger.critical(e)





def setPWMDutyCycle(percent):
    if percent > 100:
        percent = 100
    if percent < 0:
        percent = 0
    
    return percent * 10000
def setPeltierPower():
    for pin in peltierPins:
        piGPIO.hardware_PWM(pin, PWMfreq=30000, PWMduty=setPWMDutyCycle(peltierPowerLevel))

def calculatePeltierPower(h):

    global previousHumidityReading, peltierPowerLevel
    #check to see how big of an adjustment we need to make
    rhDiff = abs(h - previousHumidityReading)
    if rhDiff > .5:
        adjustment = 10
    elif rhDiff > .3:
        adjustment = 1
    else:
        adjustment = 1
    #This is setup so that the pulse width can be dynamically adjusted, but the value will never go above or below the max /min points if the system gets
    #overpowered or when the compressor is cycling.  When setting these values, keep in mind that turning off the peltier will cause the hot and cold
    #side to equalize, which will heat the condensation on the cold side and spike the humidity
    #if RH is higher than the set point by 5%, set peltier to max and stop loop
    if h > hSetpointRH:
        peltierPowerLevel = 100
        setPeltierPower()
        logger.debug('Peltier set to ' + str(peltierPowerLevel) + '. Max')

    # if RH is not higher that 5% over set point, but greater than setpoint, adjust pulse width if it's changed from last reading   
    elif h > midSetpointRH:
        #if humidity is going up increase pulse width
        if h >= previousHumidityReading:
            peltierPowerLevel += adjustment 
            logger.debug('Humidity is high and going up or stable.  Increasing pulse width')
        # if humidity is going down, decrease it.
        else:
            if rhDiff > .1: #if its going down quickly, adjust
                peltierPowerLevel -= adjustment
                logger.debug('Humidity is high,but going down too fast. Decreasing pulse width')
            else:
                logger.debug('Humidity is high,but going down slowly.  No changes made')
        #this is a failsafe incase the peltiers cant dehumidify fast enough
        if peltierPowerLevel > 100:
            peltierPowerLevel = 100
        if peltierPowerLevel < 0:
            peltierPowerLevel = 0
        setPeltierPower()
        logger.debug('Peltier set to ' + str(peltierPowerLevel))
    #if RH is 5% below setpoint, turn off peltier
    elif h < lSetpointRH:
        peltierPowerLevel = 0
        setPeltierPower()
        logger.debug('Peltier set to ' + str(peltierPowerLevel) + '. Peltier off.')
    # if RH is not lower than 5% below set point, but lower than the set point, adjust pulse width
    elif h < midSetpointRH:
        if h <= previousHumidityReading:
            peltierPowerLevel -= adjustment

            logger.debug('Humidity is low and going down or stable.  Decreasing pulse width')
        else:
            if rhDiff > .1:
                peltierPowerLevel += adjustment

                logger.debug('Humidity is low, but going up too quickly.  Increasing pulse width')
            else:
                logger.debug('Humidity is low, but going up.  no change made')
        #this is a failsafe incase the peltiers cant dehumidify fast enough
        if peltierPowerLevel < 0:
            peltierPowerLevel = 0
        if peltierPowerLevel > 100:
            peltierPowerLevel = 100
        # dont want to shut down the peltiers completely if the RH is above the min set point because it will cause a spike in RH
        # if the ESC min is 1200 and the max is 1800 this will put the pelitier power at about 16.6%
        if peltierPowerLevel == 0 and h > lSetpointRH:
            peltierPowerLevel += 15
            setPeltierPower()
        setPeltierPower()
        logger.debug('Peltier set to ' + str(peltierPowerLevel))
    previousHumidityReading = h


def listener(event):
    global tempHighSet, tempLowSet, tempSet, midSetpointRH, hSetpointRH, lSetpointRH, tOffset, hOffset
    # logger.debug(event.event_type)  # can be 'put' or 'patch'
    # logger.debug(event.path)  # relative to the reference, it seems
    # logger.debug(f"(event.data=)")  # new data at /reference/event.path. None if deleted
    if event.path == "/rhHigh":
        hSetpointRH = event.data
        settingsJSON['rhHigh'] = event.data

    elif event.path == '/rhLow':
        lSetpointRH = event.data
        settingsJSON['rhLow'] = event.data

    elif event.path == '/rhSet':
        midSetpointRH = event.data
        settingsJSON['rhSet'] = event.data

    elif event.path == '/tempSetHigh':
        tempHighSet = event.data
        settingsJSON['tempSetHigh'] = event.data

    elif event.path == '/tempSetLow':
        tempLowSet = event.data
        settingsJSON['tempSetLow'] = event.data

    elif event.path == '/tempSet':
        tempSet = event.data
        settingsJSON['tempSet'] = event.data
    
    elif event.path == '/hOffset':
        hOffset = event.data
        settingsJSON['hOffset'] = event.data
    
    elif event.path == '/tOffset':
        tOffset = event.data
        settingsJSON['tOffset'] = event.data

    try:
        with open(settingsJSONLocation, "w") as f:
            json.dump(settingsJSON, f)
    except Exception as e:
        logger.critical('Error saving settings.json')
        logger.critical(e)
try:
    settingsRef.listen(listener) #listen to the settings ref and run listener() when changes
except Exception as e:
    logger.critical('Error connecting to Firebase')
    logger.critical(e)




class TempFrameWidgets(Frame):
    
    def __init__(self):
        
        self.upImage = Image.open('icons8-sort_up.png')
        self.upTkI = ImageTk.PhotoImage(self.upImage)
        self.downImage = Image.open('icons8-sort_down.png')
        self.downTkI = ImageTk.PhotoImage(self.downImage)
        self.arrowUpButton = Button(middleFrame, image= self.upTkI, command=self.arrowUpClick)
        self.arrowDownButton = Button(middleFrame, image= self.downTkI, command= self.arrowDownClick)
        self.highSetButton = Button(middleFrame, text= 'High Set Point', command=self.hTempClick)
        self.targetSetButton = Button(middleFrame, text= 'Target Temp', command= self.targetTempClick)
        self.lowSetButton = Button(middleFrame, text= ' Low Set Point', command= self.lTempClick)
        self.offsetButton = Button(middleFrame, text= 'Offset', command= self.tempOffset)
        self.highSetValue = Label(middleFrame, text = str('%.1f' % tempHighSet)+ 'F')
        self.targetSetValue = Label(middleFrame, text = str('%.1f' % tempSet) + 'F')
        self.lowSetValue = Label(middleFrame, text = str('%.1f' % tempLowSet) + 'F')
        self.offsetValue = Label(middleFrame, text = str('%.1f' % tOffset) + 'F')
        self.selecteButton = self.highSetButton
        self.widgetList = [self.arrowUpButton,
                            self.arrowDownButton,
                            self.highSetButton,
                            self.targetSetButton,
                            self.lowSetButton,
                            self.offsetButton,
                            self.highSetValue,
                            self.targetSetValue,
                            self.lowSetValue,
                            self.offsetValue]
    

    def arrowUpClick(self):
        global tempHighSet, tempSet, tempLowSet, tOffset
        if self.selecteButton == self.highSetButton:
            tempHighSet += .5
            self.highSetValue.config(text = str(tempHighSet) + 'F')
            settingsJSON['tempHighSet'] = tempHighSet
        elif self.selecteButton == self.targetSetButton:
            tempSet += .5
            self.targetSetValue.config(text = str(tempSet) + 'F')
            settingsJSON['tempSet'] = tempSet
        elif self.selecteButton == self.lowSetButton:
            tempLowSet += .5
            self.lowSetValue.config(text = str(tempLowSet) + 'F')
            settingsJSON['tempLowSet'] = tempLowSet
        elif self.selecteButton == self.offsetButton:
            tOffset += .5
            self.offsetValue.config(text = str(tOffset) + 'F')
            settingsJSON['tOffset'] = tOffset
        try:
            with open(settingsJSONLocation, "w") as f:
                json.dump(settingsJSON, f)
        except Exception as e:
                logger.critical('Error saving settings.json')
                logger.critical(e)
        try:
            settingsRef.set(settingsJSON)
        except Exception as e:
            logger.critical('Error connecting to Firebase')
            logger.critical(e)
        logger.debug('arrow up pressed')
    def arrowDownClick(self):
        global tempHighSet, tempSet, tempLowSet, tOffset
        if self.selecteButton == self.highSetButton:
            tempHighSet -= .5
            self.highSetValue.config(text = str(tempHighSet) + 'F')
            settingsJSON['tempHighSet'] = tempHighSet
        elif self.selecteButton == self.targetSetButton:
            tempSet -= .5
            self.targetSetValue.config(text = str(tempSet) + 'F')
            settingsJSON['tempSet'] = tempSet
        elif self.selecteButton == self.lowSetButton:
            tempLowSet -= .5
            self.lowSetValue.config(text = str(tempLowSet) + 'F')
            settingsJSON['tempLowSet'] = tempLowSet
        elif self.selecteButton == self.offsetButton:
            tOffset -= .5
            self.offsetValue.config(text = str(tOffset) + 'F')
            settingsJSON['tOffset'] = tOffset
        try:
            with open(settingsJSONLocation, "w") as f:
                json.dump(settingsJSON, f)
        except Exception as e:
            logger.critical('Error saving settings.json')
            logger.critical(e)
        try:
            settingsRef.set(settingsJSON)
        except Exception as e:
            logger.critical('Error connecting to Firebase')
            logger.critical(e)
        logger.debug('arrow down pressed')
    def hTempClick(self):
        self.selecteButton = self.highSetButton
        logger.debug('high temp pressed')
    def targetTempClick(self):
        self.selecteButton = self.targetSetButton
        logger.debug('target temp pressed')
    def lTempClick(self):
        self.selecteButton = self.lowSetButton
        logger.debug('low temp pressed')
    def tempOffset(self):
        self.selecteButton = self.offsetButton
        logger.debug('temp offset pressed')

class HumidityFrameWidgets(Label, Button):
    def __init__(self):
        
        self.upImage = Image.open('icons8-sort_up.png')
        self.upTkI = ImageTk.PhotoImage(self.upImage)
        self.downImage = Image.open('icons8-sort_down.png')
        self.downTkI = ImageTk.PhotoImage(self.downImage)
        self.arrowUpButton = Button(middleFrame, image= self.upTkI, command= self.arrowUpClick)
        self.arrowDownButton = Button(middleFrame, image= self.downTkI, command= self.arrowDownClick)
        self.highSetButton = Button(middleFrame, text= 'High Set Point', command=self.hRhClick)
        self.targetSetButton = Button(middleFrame, text= 'Target Humidity', command= self.targetRhClick)
        self.lowSetButton = Button(middleFrame, text= ' Low Set Point', command= self.lRhClick)
        self.humidifierButton = Button(middleFrame,text= ' Humidifier On Set Point')
        self.offsetButton = Button(middleFrame, text= 'Offset', command= self.rhOffset)
        self.highSetValue = Label(middleFrame, text = str('%.1f' % hSetpointRH)+ '%')
        self.targetSetValue = Label(middleFrame, text = str('%.1f' % midSetpointRH)+ '%')
        self.lowSetValue = Label(middleFrame, text = str('%.1f' % lSetpointRH)+ '%')
        self.offsetValue = Label(middleFrame, text = str('%.1f' % hOffset)+ '%')
        self.humidifierOnValue = Label(middleFrame, text= str('%.1f' % humidifierOn)+ '%')
        self.selecteButton = self.highSetButton
        self.widgetList = [self.arrowUpButton,
                            self.arrowDownButton,
                            self.highSetButton,
                            self.targetSetButton,
                            self.lowSetButton,
                            self.offsetButton,
                            self.highSetValue,
                            self.targetSetValue,
                            self.lowSetValue,
                            self.offsetValue,
                            self.humidifierOnValue]
    
    def arrowUpClick(self):
        global hSetpointRH, midSetpointRH, lSetpointRH, hOffset, humidifierOn
        if self.selecteButton == self.highSetButton:
            hSetpointRH += .5
            self.highSetValue.config(text = str(hSetpointRH) + '%')
            settingsJSON['rhHigh'] = hSetpointRH
        elif self.selecteButton == self.targetSetButton:
            midSetpointRH += .5
            self.targetSetValue.config(text = str(midSetpointRH) + '%')
            settingsJSON['rhSet'] = midSetpointRH
        elif self.selecteButton == self.lowSetButton:
            lSetpointRH += .5
            self.lowSetValue.config(text = str(lSetpointRH) + '%')
            settingsJSON['rhLow'] = lSetpointRH
        elif self.selecteButton == self.offsetButton:
            hOffset += .5
            self.offsetValue.config(text = str(hOffset) + '%')
            settingsJSON['hOffset'] = hOffset
        elif self.selecteButton == self.humidifierButton:
            humidifierOn += .5
            self.humidifierOnValue.config(text=str('%.1f' % humidifierOn)+ '%')
            settingsJSON['humidifierOn'] = humidifierOn
        try:
            with open(settingsJSONLocation, "w") as f:
                json.dump(settingsJSON, f)
        except Exception as e:
            
            logger.critical('Error saving settings.json')
            logger.critical(e)
        try:
            settingsRef.set(settingsJSON)
        except Exception as e:
            logger.critical('Error connecting to Firebase')
            logger.critical(e)
        logger.debug('arrow up pressed')
    def arrowDownClick(self):
        global hSetpointRH, midSetpointRH, lSetpointRH, hOffset, humidifierOn
        if self.selecteButton == self.highSetButton:
            hSetpointRH -= .5
            self.highSetValue.config(text = str(hSetpointRH) + '%')
            settingsJSON['rhHigh'] = hSetpointRH
        elif self.selecteButton == self.targetSetButton:
            midSetpointRH -= .5
            self.targetSetValue.config(text = str(midSetpointRH) + '%')
            settingsJSON['rhSet'] = midSetpointRH
        elif self.selecteButton == self.lowSetButton:
            lSetpointRH -= .5
            self.lowSetValue.config(text = str(lSetpointRH) + '%')
            settingsJSON['rhLow'] = lSetpointRH
        elif self.selecteButton == self.offsetButton:
            hOffset -= .5
            self.offsetValue.config(text = str(hOffset) + '%')
            settingsJSON['hOffset'] = hOffset
        elif self.selecteButton == self.humidifierButton:
            humidifierOn -= .5
            self.humidifierOnValue.config(text=str('%.1f' % humidifierOn)+ '%')
            settingsJSON['humidifierOn'] = humidifierOn
        try:
            with open(settingsJSONLocation, "w") as f:
                json.dump(settingsJSON, f)
        except Exception as e:
                logger.critical('Error saving settings.json')
                logger.critical(e)
        try:
            settingsRef.set(settingsJSON)
        except Exception as e:
            logger.critical('Error connecting to Firebase')
            logger.critical(e)
        logger.debug('arrow down pressed')
    def hRhClick(self):
        self.selecteButton = self.highSetButton
        logger.debug('high temp pressed')
    def targetRhClick(self):
        self.selecteButton = self.targetSetButton
        logger.debug('target temp pressed')
    def lRhClick(self):
        self.selecteButton = self.lowSetButton
        logger.debug('low temp pressed')
    def rhOffset(self):
        self.selecteButton = self.offsetButton
        logger.debug('temp offset pressed')

class StatsFrameWidgets(Label):
    def __init__(self):
        self.widgetList = []
        self.tempLabel = Label(middleFrame,text="Current\nTemperature", font= ("TkDefaultFont", 10))
        self.rhLabel = Label(middleFrame, text= "Current\nHumidity", font= ("TkDefaultFont", 10))
        self.tempValueLabel = Label(middleFrame, text = str(currentTemp) + 'F')
        self.rhValueLabel = Label(middleFrame, text = str(currentRH) + '%')
        self.twentyFourAvgTempLabel = Label(middleFrame, text = '24h Average\nTemperature', font=("TkDefaultFont", 10))
        self.twentyFourAvgHumidityLabel = Label(middleFrame, text = '24h Average\nHumidity', font=("TkDefaultFont", 10), pady=10)
        
        self.twentyFourAvgHumidityValue = Label(middleFrame, text = str('%.1f' % averageRH) + '%')
        self.twentyFourAvgTempValue = Label(middleFrame, text = str('%.2f' % averageTemp) + 'F')
        self.peltierPower = Label(middleFrame, text = 'Peltier Power', font=("TkDefaultFont", 10))
        self.peltierPowerValue = Label(middleFrame,text = '0%')

SFW = StatsFrameWidgets()
TFW = TempFrameWidgets()
HFW = HumidityFrameWidgets()

def calculateESCPeltierPower():
    EscPowerRange = peltierEscMax - peltierEscMin
    percent = ((peltierESCPulseWidth - peltierEscMin) / EscPowerRange) * 100
    return percent
def calcAverageTandH():
    global averageTemp, averageRH
    timeStamp= datetime.now()
    previousTime = timeStamp - timedelta(hours=24)
    timeStampNow = timeStamp.strftime("%m-%d-%Y %H:%M:%S")
    previousTime = previousTime.strftime("%m-%d-%Y %H:%M:%S")
    averageDF = df.loc[previousTime : timeStampNow]
    
    try:
        averageTemp = averageDF['Temp'].mean()
        averageRH = averageDF['RH'].mean()
    except Exception as e:
        logger.critical('exception in clacAverageTandH()')
        logger.critical(e)




def setPeltierESC(h):
    
    global peltierESCPulseWidth, previousHumidityReading
    #check to see how big of an adjustment we need to make
    rhDiff = abs(h - previousHumidityReading)
    if rhDiff > .5:
        adjustment = 100
    elif rhDiff > .3:
        adjustment = 30
    else:
        adjustment = 5
    #This is setup so that the pulse width can be dynamically adjusted, but the value will never go above or below the max /min points if the system gets
    #overpowered or when the compressor is cycling.  When setting these values, keep in mind that turning off the peltier will cause the hot and cold
    #side to equalize, which will heat the condensation on the cold side and spike the humidity
    #if RH is higher than the set point by 5%, set peltier to max and stop loop
    if h > hSetpointRH:
        peltierESCPulseWidth = peltierEscMax
        piGPIO.set_servo_pulsewidth(peltierESC, peltierESCPulseWidth)
        logger.debug('Peltier set to ' + str(peltierESCPulseWidth) + '. Max')

    # if RH is not higher that 5% over set point, but greater than setpoint, adjust pulse width if it's changed from last reading   
    elif h > midSetpointRH:
        #if humidity is going up increase pulse width
        if h >= previousHumidityReading: 
            peltierESCPulseWidth += adjustment 
            logger.debug('Humidity is high and going up or stable.  Increasing pulse width')
        # if humidity is going down, decrease it.
        else:
            if rhDiff > .1: #if its going down quickly, adjust
                peltierESCPulseWidth -= adjustment
                logger.debug('Humidity is high,but going down too fast. Decreasing pulse width')
            else:
                logger.debug('Humidity is high,but going down slowly.  No changes made')
        #this is a failsafe incase the peltiers cant dehumidify fast enough
        if peltierESCPulseWidth > peltierEscMax:
            peltierESCPulseWidth = peltierEscMax
        piGPIO.set_servo_pulsewidth(peltierESC, peltierESCPulseWidth)
        logger.debug('Peltier set to ' + str(peltierESCPulseWidth))
    #if RH is 5% below setpoint, turn off peltier
    elif h < lSetpointRH:
        peltierESCPulseWidth = peltierEscMin
        piGPIO.set_servo_pulsewidth(peltierESC, peltierESCPulseWidth)
        logger.debug('Peltier set to ' + str(peltierESCPulseWidth) + '. Peltier off.')
    # if RH is not lower than 5% below set point, but lower than the set point, adjust pulse width
    elif h < midSetpointRH:
        if h <= previousHumidityReading:
            peltierESCPulseWidth -= adjustment
            logger.debug('Humidity is low and going down or stable.  Decreasing pulse width')
        else:
            if rhDiff > .1:
                peltierESCPulseWidth += adjustment
                logger.debug('Humidity is low, but going up too quickly.  Increasing pulse width')
            else:
                logger.debug('Humidity is low, but going up.  no change made')
        #this is a failsafe incase the peltiers cant dehumidify fast enough
        if peltierESCPulseWidth < peltierEscMin:
            peltierESCPulseWidth = peltierEscMin
        # dont want to shut down the peltiers completely if the RH is above the min set point because it will cause a spike in RH
        # if the ESC min is 1200 and the max is 1800 this will put the pelitier power at about 16.6%
        if peltierESCPulseWidth == peltierEscMin and h > lSetpointRH:
            peltierESCPulseWidth = peltierEscMin + 100
        piGPIO.set_servo_pulsewidth(peltierESC, peltierESCPulseWidth)
        logger.debug('Peltier set to ' + str(peltierESCPulseWidth))
    previousHumidityReading = h
    
def fridgeOn():
    logger.debug("fridgeOn() started")
    piGPIO.write(fridgePin, 1)
    logger.debug("fridgeOn() finished")
def fridgeOff():
    logger.debug("fridgeOff() started")
    piGPIO.write(fridgePin, 0)
    logger.debug("fridgeOff() finished")
def turnHumidifierOn():
    logger.debug("humidifierOn() started")
    piGPIO.write(humidifierPin, 1)
    logger.debug("humidifierOn() finished")
def turnHumidifierOff():
    logger.debug("humidifierOff() started")
    piGPIO.write(humidifierPin, 0)
    logger.debug("humidifierOff() finished")

def handleFridge(t):
    global isFridgeOn
    logger.debug("isFridgeOn=" + str(isFridgeOn))
    
    if t > tempHighSet and isFridgeOn == False:
        fridgeOn()
        isFridgeOn = True
    if t <= tempSet and isFridgeOn == True:
        fridgeOff()
        isFridgeOn = False

def handleHumidifier(h):
    global isHumidifierOn
    print(humidifierOn)
    print(isHumidifierOn)
    if h < humidifierOn and isHumidifierOn == False:
        turnHumidifierOn()
        isHumidifierOn = True
    # else:
    #     turnHumidifierOff()
    #     isHumidifierOn = False
    if h > humidifierOn and isHumidifierOn == True:
       turnHumidifierOff()
       isHumidifierOn = False



def getTandH():
    global df, graphDF, currentTemp, currentRH, writeData
    #Read Temp and Hum from DHT22
    try:
        t, h = ((dhtDevice.temperature * 1.8) + 32, dhtDevice.humidity + hOffset)

        timeStamp = datetime.now()
        timeStamp = timeStamp.strftime("%m-%d-%Y %H:%M:%S")



        logger.debug(timeStamp + 'Temp={0:0.2f}*F  Humidity={1:0.1f}%'.format(t,h))
        # calculatePeltierPower(h)
        # handleFridge(t)
        # handleHumidifier(h)
        # Set this bool up by the peltierPins.  If using the custom controler, will us PWM to adjust power.
        # If using an ESC, will adjust power using servo pulse width
        if customPeltierControler == True:
            #threading.Thread(target=calculatePeltierPower,args=(h,)).start()
            calculatePeltierPower(h)
        else:
            #threading.Thread(target=setPeltierESC,args=(h,)).start()
            setPeltierESC(h)
        
        #threading.Thread(target=handleFridge, args=(t,)).start()
        #threading.Thread(target=handleHumidifier, args=(h,)).start()
        handleFridge(t)
        handleHumidifier(h)

        if t < 90 and h <101: # and writeData == True:
            with open(filename, 'a') as f: #will open the file and close it once the block of code is done
                #here T and F are written to the CSV as strings, but we need to convert them back to floats later so that it doesnt mess up the DF
                f.write('\n' + timeStamp + ',' + '{0:0.2f},{1:0.1f}'.format(t,h) + ',' + str(tempSet) + ',' + str(midSetpointRH))
            
            #convert back to float so it doesnt mess up the DF
            t = float('%.2f' % t)
            h = float('%.1f' % h)
            # create a new DF to append to existing DFs
            data = {'Temp': t, 'RH': h, 'Temp Set': tempSet, 'RH Set': midSetpointRH}#data for pandas
            newDF = pd.DataFrame(data, index = pd.to_datetime([timeStamp]))
            #upload to Firebase

            currentData = {'Time': timeStamp,'Temp': t, 'RH': h, 'Temp Set': tempSet, 'RH Set': midSetpointRH}
            historyData = {'Temp': t, 'RH': h, 'Temp Set': tempSet, 'RH Set': midSetpointRH} #data for firebase with time stamp
            try:
                historyRef = db.reference("/History/" + str(timeStamp + "/"))
                currentDataRef.set(currentData)
                historyRef.set(historyData)
            except Exception as e:
                logger.critical('Error connecting to Firebase')
                logger.critical(e)
            # logger.debug(data)
            graphDF = graphDF.append(newDF)
            df = df.append(newDF)

        if len(df) > 69120: #check to see if there are more than 4 days of data in the list.
            n = len(df) - 69120
            df = df.iloc[n:] #if there is, then remove the oldest
        if len(graphDF) > graphDFlen:
            n = len(graphDF) - graphDFlen
            graphDF = graphDF.iloc[n:]
        # logger.debug(df)
        # logger.debug(len(graphDF))
        currentTemp = t
        currentRH = h
        # calcAverageTandH()
        # animate()
    except Exception as e:
        logger.critical('exception in getTandH()')
        logger.critical(e)
        
    #root.after(5000, threadGetTandH) #schedules the function to run again in 2.5 seconds
    root.after(5000, getTandH)
    
def animate(i):
    logger.debug('animate')

    ax.clear()
    ax.plot(graphDF)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid(True)
    ax.xaxis_date()     # interpret the x-axis values as dates
    fig.autofmt_xdate() # make space for and rotate the x-axis tick labels



def updateTime():
    string = strftime('%-I:%M:%S %p')
    topBar3.config(text = string)
    topBar3.after(1000, updateTime)

def updateCurrentTemp():
    SFW.tempValueLabel.config(text = str(currentTemp) + 'F')
    SFW.tempValueLabel.after(5000, updateCurrentTemp)

def updateAvgTemp():
    calcAverageTandH()
    t = '%.2f' % averageTemp
    SFW.twentyFourAvgTempValue.config(text = str(t) + 'F')
    SFW.twentyFourAvgTempValue.after(60000, updateAvgTemp)

def updateCurrentRH():
    SFW.rhValueLabel.config(text = str(currentRH) + '%')
    SFW.rhValueLabel.after(5000, updateCurrentRH)

def updateAvgRH():
    calcAverageTandH()
    h = '%.1f' % averageRH
    SFW.twentyFourAvgHumidityValue.config(text = str(h) + '%')
    SFW.twentyFourAvgHumidityValue.after(60000, updateAvgRH)

def updatePeltierPower():
    if customPeltierControler == True:
        percent = str('%.1f' % peltierPowerLevel) + '%'
        SFW.peltierPowerValue.config(text= percent)
        SFW.peltierPowerValue.after(5000,updatePeltierPower)
    else:
        percent = str('%.1f' % calculateESCPeltierPower()) + '%'
        SFW.peltierPowerValue.config(text= percent)
        SFW.peltierPowerValue.after(5000,updatePeltierPower)

# def updatePeltierPower():

    # percent = str('%.1f' % pelti) + '%'


def allChildren (window) :
    _list = window.winfo_children()

    for item in _list :
        if item.winfo_children() :
            _list.extend(item.winfo_children())

    return _list

def graph(time):
    logger.debug('graph button clicked')
    # logger.debug(style.available)
    style.use('seaborn-bright')
    timeStamp= datetime.now()
    previousTime = timeStamp - timedelta(hours=time)
    timeStampNow = timeStamp.strftime("%m-%d-%Y %H:%M:%S")
    previousTime = previousTime.strftime("%m-%d-%Y %H:%M:%S")
    # global filteredDF
    # filteredDF = df.loc[previousTime : timeStampNow]
    # logger.debug(filteredDF)
    global graphDF, graphDFlen, line

    graphDF = df.loc[previousTime : timeStampNow] #this creates the DF that will be used for animating the graph
    graphDFlen = len(graphDF) #global variable so we know how long the list should be for the given graph
    logger.debug(len(graphDF))
    
    # del filteredDF['Time']
    # logger.debug(len(filteredDF))
    # filteredDF.plot()
    # SFW.widgetList = allChildren(middleFrame)
    # # logger.debug(widgetList)
    # for item in SFW.widgetList:
    #     item.forget()#use destroy.  forget just hides it
    
    
    ax.clear()
    line = ax.plot(graphDF) #do this first so that the dates can be formatted
    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) #format dates as hours and minutes
    ax.xaxis_date()     # interpret the x-axis values as dates
    fig.autofmt_xdate() # make space for and rotate the x-axis tick labels

    # plt.show() # this will load the graph in a separate window.

    #load graph on canvas in TK
    # lf = ttk.Frame(middleFrame)
    lf.grid(row=0, column=2, padx=0, pady=0, columnspan=4, rowspan=4)
    # canvas = FigureCanvasTkAgg(fig, master = lf)
    canvas.draw()
    # canvas.get_tk_widget().grid(row=0, column=3, columnspan= 5)
    canvas.get_tk_widget().pack(side= RIGHT, fill= BOTH, expand= True)

    

def button1Click():
    logger.debug("first button pressed")
    graph(2)
    logger.debug("done")
def button2Click():
    graph(5)
    logger.debug("second button pressed")
def button3Click():
    graph(12)
    logger.debug("third button pressed")
def button4Click():
    graph(24)
    logger.debug("fourth button pressed")
def button5Click():
    graph(96)
    logger.debug("fifth button pressed")
def humidityButtonClick():
    currentWidgets = allChildren(middleFrame)
    for widget in currentWidgets:
        widget.grid_forget()
    HFW.arrowUpButton.grid(row = 0, column = 0, sticky='nsew', rowspan= 2, columnspan=2)
    HFW.arrowDownButton.grid(row = 2, column = 0, sticky='nsew', rowspan= 2, columnspan=2)
    HFW.highSetButton.grid(row = 0, column = 2, sticky='nsew', columnspan=2)
    HFW.targetSetButton.grid(row = 1, column = 2, sticky='nsew', columnspan=2)
    HFW.lowSetButton.grid(row = 2, column = 2, sticky='nsew', columnspan=2)
    HFW.offsetButton.grid(row = 3, column = 2, sticky='nsew', columnspan=2)
    HFW.highSetValue.grid(row = 0, column = 4, sticky='nsew', columnspan=2)
    HFW.targetSetValue.grid(row = 1, column = 4, sticky='nsew', columnspan=2)
    HFW.lowSetValue.grid(row = 2, column = 4, sticky='nsew', columnspan=2)
    HFW.offsetValue.grid(row = 3, column = 4, sticky='nsew', columnspan=2)

    x , y = middleFrame.grid_size() #(columns, rows)

    for c in range(0,x):
        Grid.columnconfigure(middleFrame, c, weight = 1)
    for r in range(0,y):
        Grid.rowconfigure(middleFrame, r, weight = 1)
    logger.debug('humidity button pressed')
def tempBottonClick():
    currentWidgets = allChildren(middleFrame)
    for widget in currentWidgets: 
        widget.grid_forget()
    TFW.arrowUpButton.grid(row = 0, column = 0, sticky='nsew', rowspan= 2, columnspan=2)
    TFW.arrowDownButton.grid(row = 2, column = 0, sticky='nsew', rowspan= 2, columnspan=2)
    TFW.highSetButton.grid(row = 0, column = 2, sticky='nsew', columnspan=2)
    TFW.targetSetButton.grid(row = 1, column = 2, sticky='nsew', columnspan=2)
    TFW.lowSetButton.grid(row = 2, column = 2, sticky='nsew', columnspan=2)
    TFW.offsetButton.grid(row = 3, column = 2, sticky='nsew', columnspan=2)
    TFW.highSetValue.grid(row = 0, column = 4, sticky='nsew', columnspan=2)
    TFW.targetSetValue.grid(row = 1, column = 4, sticky='nsew', columnspan=2)
    TFW.lowSetValue.grid(row = 2, column = 4, sticky='nsew', columnspan=2)
    TFW.offsetValue.grid(row = 3, column = 4, sticky='nsew', columnspan=2)

    x , y = middleFrame.grid_size() #(columns, rows)

    for c in range(0,x):
        Grid.columnconfigure(middleFrame, c, weight = 2)
    for r in range(0,y):
        Grid.rowconfigure(middleFrame, r, weight = 2)
    # Grid.columnconfigure(middleFrame, 4, weight = 0)
    Grid.columnconfigure(middleFrame, 5, weight = 0)
    Grid.rowconfigure(middleFrame, 4, weight = 0)
    Grid.rowconfigure(middleFrame, 5, weight = 0)
    logger.debug('temp button pressed')
def programsButtonClick():
    logger.debug('Programs button pressed')
def tecButtonClick():
    logger.debug('TEC button pressed')


def settingsButtonClick():
    bottomButtonsToRemove = bottomBarFrame.winfo_children()
    for button in bottomButtonsToRemove:
        button.destroy()
    statWidgets = middleFrame.winfo_children()
    for widget in statWidgets:
        widget.grid_forget()

    

    button1 = Button(bottomBarFrame, text = "Humidity", command = humidityButtonClick, height = barHeight) #mac ignores bg color for some reason
    button2 = Button(bottomBarFrame, text = "Temp", command = tempBottonClick, height = barHeight)
    button3 = Button(bottomBarFrame, text = "Programs", command = programsButtonClick, height = barHeight)
    
    bottomBarFrame.rowconfigure(0,weight=1)
    columnNum = 0
    bottomBarList = [button1, button2, button3]
    for button in bottomBarList:
        bottomBarFrame.columnconfigure(columnNum, weight=1)
        columnNum+=1
    #for some reason tkinter remembers the number of columns that ever existed and will space them like they are there if you dont put this
    bottomBarFrame.columnconfigure(3, weight=0) 
    bottomBarFrame.columnconfigure(4, weight=0)
    button1.grid(row = 0, column = 0, sticky='nsew')
    button2.grid(row = 0, column = 1, sticky='nsew')
    button3.grid(row = 0, column = 2, sticky='nsew')

    bottomBarFrame.pack(fill= 'x')#this makes the buttons fill the width of the screen

    
    tempBottonClick()
    

    logger.debug("settings button pressed")

def statsButtonClick():
    
    graph(2)
    # bottomBarFrame.pack_forget()
    # global settingsWidgets 
    bottomButtonsToRemove = bottomBarFrame.winfo_children()
    for button in bottomButtonsToRemove:
        button.destroy()
    # global settingsWidgets 
    # settingsWidgets = middleFrame.winfo_children()
    global TFW, HFW
    for widget in TFW.widgetList:
        widget.destroy()
    TFW = TempFrameWidgets()
    for widget in HFW.widgetList:
        widget.destroy()
    HFW = HumidityFrameWidgets()
    setupStatsMiddleFrame()
    Grid.rowconfigure(bottomBarFrame, 0,weight=1)
    Grid.columnconfigure(bottomBarFrame,0,weight=1)
    button1 = Button(bottomBarFrame, text = "2 Hours", command = button1Click, height =barHeight) #mac ignores bg color for some reason
    button2 = Button(bottomBarFrame, text = "5 Hours", command = button2Click, height = barHeight)
    button3 = Button(bottomBarFrame, text = "12 Hours", command = button3Click, height = barHeight)
    button4 = Button(bottomBarFrame, text = "1 Day", command = button4Click, height = barHeight)
    button5 = Button(bottomBarFrame, text = "4 days", command = button5Click, height = barHeight)


    columnNum = 0
    bottomBarList = [button1, button2, button3, button4, button5]
    for button in bottomBarList:
        Grid.columnconfigure(bottomBarFrame, columnNum, weight=1)
        columnNum+=1

    button1.grid(row = 0, column = 0, sticky='nsew')
    button2.grid(row = 0, column = 1, sticky='nsew')
    button3.grid(row = 0, column = 2, sticky='nsew')
    button4.grid(row = 0, column = 3, sticky='nsew')
    button5.grid(row = 0, column = 4, sticky='nsew')
    logger.debug("stats button pressed")
    bottomBarFrame.pack(fill= 'x') #this makes the buttons fill the width of the screen


    middleFrame.pack(fill= 'x') #since the widgets are already created, this will put them back in their place
    #logger.debug(middleFrame.winfo_height(), topBarFrame.winfo_height(), bottomBarFrame.winfo_height())


def setupStatsMiddleFrame():

    SFW.tempLabel.grid(row = 0, column = 0, sticky='nsew')
    SFW.tempValueLabel.grid(row = 0, column = 1, sticky='nsew', padx = 10)
    SFW.rhLabel.grid(row = 1, column = 0, sticky='nsew')   
    SFW.rhValueLabel.grid(row = 1, column = 1, sticky='nsew', padx = 10)
    SFW.twentyFourAvgTempLabel.grid(row = 2, column = 0, sticky='nsew')
    SFW.twentyFourAvgHumidityLabel.grid(row = 3, column = 0, sticky='nsew')
    SFW.twentyFourAvgTempValue.grid(row = 2, column = 1, sticky='nsew', padx = 10)
    SFW.twentyFourAvgHumidityValue.grid(row = 3, column = 1, sticky='nsew', padx = 10)
    SFW.peltierPower.grid(row = 5, column= 0, sticky='nsew')
    SFW.peltierPowerValue.grid(row = 5, column = 1, sticky = 'nsew', padx = 10)

    x , y = middleFrame.grid_size() #(columns, rows)
    for c in range(0,x-1):
        Grid.columnconfigure(middleFrame, c, weight = 1)

    for r in range(0,y-1):
        Grid.rowconfigure(middleFrame, r, weight = 1)

    # middleFrame.pack(fill= 'x')

def getLengthOfDaysMS(days):
    secondsInDay = 86400
    return (secondsInDay * days) * 1000

def clearOldFirebaseData():
    try:
        historyRef.delete()
        dfJSON = df.to_json(orient='index')
        historyRef.set(dfJSON)
    except Exception as e:
        logger.critical('Error connecting to Firebase')
        logger.critical(e)

def splitCSV():
    os.system('mv CharcTankData.csv CharcTankData.bak')
    with open(filename, 'a') as f: # create new file with CSV headers
        f.write('Time,Temp,RH,Temp Set,RH Set')
    os.system("sed -i '1d' CharcTankData.bak") #remove CSV headers
    os.system('cat CharcTankData.old CharcTankData.bak > CharcTankData.old')
    lengthOfDaysMS = getLengthOfDaysMS(4)
    root.after(lengthOfDaysMS, splitCSV)
    clearOldFirebaseData()

def setValues():
    global tempSet, tempHighSet, tempLowSet, hSetpointRH, lSetpointRH, midSetpointRH, humidifierOn, timerIndex
    


    timerIndex +=1

# def threadGetTandH():
    
#     getTandHthread = threading.Thread(target=getTandH, daemon=True).start()

barHeight = 2
pixel = PhotoImage(width=1, height=1)

topBar1 = Label(topBarFrame, text = "CharcTankOS", height = barHeight)
topBar2 = Button(topBarFrame, text = "Stats", command = statsButtonClick, height = barHeight)
topBar3 = Label(topBarFrame, height = barHeight) #text is set by updateTime()
topBar4 = Button(topBarFrame, text = "Settings", command = settingsButtonClick, height = barHeight)
topBar5 = Button(topBarFrame, text = "X", command =root.quit, height = barHeight)
updateTime()
Grid.rowconfigure(topBarFrame, 0,weight=1)
# Grid.columnconfigure(topBarFrame,0,weight=1)
columnNum = 0
topBarList = [topBar1, topBar2, topBar3, topBar4, topBar5]
for button in topBarList:
   Grid.columnconfigure(topBarFrame, columnNum, weight=1)
   columnNum+=1

topBar1.grid(row = 0, column = 2, sticky = "nsew")
topBar2.grid(row = 0, column = 0, sticky = "nsew")
topBar4.grid(row = 0, column = 1, sticky = "nsew")
topBar3.grid(row = 0, column = 3, sticky = "nsew")
topBar5.grid(row = 0, column = 4, sticky = "nsew")

topBarFrame.pack(fill='x')







statsButtonClick()
setupStatsMiddleFrame()
graph(2)
updateCurrentTemp()
updateCurrentRH()
updateAvgTemp()
updateAvgRH()
updatePeltierPower()


##MARK:
root.after(0, getTandH) #reads temp and humidity every 5 seconds in tkinter loop
#root.after(0, threadGetTandH)
ani = animation.FuncAnimation(fig, animate, interval = 5000)
lengthOfDaysMS = getLengthOfDaysMS(4)
#root.after(lengthOfDaysMS, splitCSV)


root.mainloop() #this creates the loop that keep the script running and refreshes the display

