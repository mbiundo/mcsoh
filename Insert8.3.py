#!/usr/bin/python
#---------------------------------------------------------------
# Marc Biundo 6/1/16 
# Version 8.3
# This program is designed to facilitate communications with multiple Morningstar SunSaver MPPT Solar Controlers Remoteley via TCP/IP.
# The goal is to provide SOH power system monitioring, and provide historical trending to assess battery performance and sizing. 
# We may be able to anticipate failures of battery systems and help schedule preventitive maintenance for battery banks.
# The MPPT requires a MorningStar Serial MSC.
# Since the MPPT+MSC pair would not simply commuicate via TCP/IP or Modbus prototocols, a Arduino MicroController is acting
# as an interpreter between controller and radio: [mppt+MSC]----[interpreter]-----[rs232 serial port]--------[rs232 serial port]TCP/IP Radio 
# This code is prototype in nature once extensive bench and field testing can be completed.
# This code nor the ancilliary hardware will modify the state of the MPPT. It is READ ONLY!
# The tranlator Arduino hardware draws 20 milli amps or consumes .24Watts of power.
#
# This program takes the data from the mppt and inserts it into an RRDTool Database.
# All entries are raw format for post processing with RRDTool graphing utilities.
# Additionall performance (timing values) from this program are also inserted into the DB.

# Multiple mppt's can be called. Be sure to edit the StationList.txt
# Example: 
#       MARC_mppt,192.168.33.11,5001
#		LCCR_mppt,192.168.33.1,5005
#		FISH_mppt,192.168.33.100,5001
#
#    Placing a # in front of the file will cause it to be skipped.
#
#
# Standard output is written to a file as defined in the code below...
# It was decided to have a simple CSV format for quick look status. It can be modified if needed.
# The RRDTool graphing utilities can / will provide extensive calculations and graphing utilities
# Of all MPPT registers.
#
# Example LogFile.txt output:
#
#	MARC_mppt,7/24/2016,17:43:11, LoadState,LOAD_ON, VBatt,13.46,V, Vlvd,11.00,V, Vdiff,2.46,V, ChargeState,FLOAT, Comm_Duration, 0.317, seconds,
#	LCCR_mppt,7/24/2016,17:43:16, LoadState,LOAD_ON, VBatt,13.51,V, Vlvd,11.00,V, Vdiff,2.51,V, ChargeState,FLOAT, Comm_Duration, 4.306, seconds,
#	FISH_mppt,7/24/2016,17:43:21, LoadState,START, VBatt,0.00,V, Vlvd,0.00,V, Vdiff,0.00,V, ChargeState,START, Comm_Duration, 4.888, seconds,
#
# FISH is a unit in test mode with no MPPT attached. That's why the values are 0.00....It's a mode to help validate / qualify Interpeters....
#
#
# Round Robin Database Tool is the database of choice for this program. Strict layout of RRD Tool Creation formats must be followed.
# The convension for this program is to name the RRD Database as: StationName_mppt.rrd i.e. LCCR_mppt.rrd
# future versions that track other SOH data will use a similar convention. This will help with graphing from multiple RRD databases...
# A ten year database is approximatly 1M bytes in size. And since it is a ring, it will overwrite in 10 years.
#
#
#
# Script to retrieve data sent via W/LAN connection from
# Intuicom or Freewave 900Mhz radio. This in turn was retrieved from the SSMPPT
# via the MSC(Serial MorningStar) module speaking Modbus protocol that was translated
# by the Arduino Pro Mini translator.
#
# Baud rate on Translator is 19200 8N1, no null needed... Direct connect.
# If you connect directly to translator via serial, use putty. 
# The LED will blink every 5 sec. It's sending the string. This string contains the 45
# mppt registers...
#
# Output from this program is redirected(stdio) to the log file listed below.
# If the log file does not exist, it will be created.
#
# Also the parameter names and their scale factors are in an ordered
# list so that the parameters message index can be used to get the
# name, scale factor, and units for later use - see example below.
#
# In the code below the in string is split into a list of parameters
# The header items are 'popped' out so a not to clutter the list. That makes
# the MPPT items start at offset zero (0).
#
# In the code script towards the end of the file there is a loop that allows
# the retrieval of an item from 'param' list using the MPPT Modbus spec
# 'Logical Addr' value. So to read the Battery Voltage (ADC_VB_F), which
# by spec is item 9, you can enter '9' and it will pull that one out. This
# works for all values in the list. A simple Enter at the prompt will exit
# this loop.
#
# After that you can request the logged data from the MPPT or enter '0' for
# the number of records to read and it will exit the program (script).
#
# 3/24/16: all bit fields are decoded except the 24 bit alarm HI/LO parameter
#-----------------------------------------------------------------------
# 7/2/16 Biundo 
#-----------------------------------------------------------------------
# Check for a "commented out" line in StationList and do not use it..
# Made print statements more CSV like. Make sure to add / maniplulate commas to avoid new lines.
# Added load state so we could see when the LVD_WARNING arrives if the RRD insert misses it.
# Added charge state in log.
# The original print statements are commented out... Should you want them for debugging purposes later.
#-----------------------------------------------------------------------
#-----------------------------------------------------------------------
# 7/10/16 Biundo 
#-----------------------------------------------------------------------
# Exception Handeling added for socket comms. This includes some timing information to assess performance.
# There is now only on socket timeout call. There were several in previous revisions for testing.
# 
#-----------------------------------------------------------------------
# 7/19/16 Biundo 
#-----------------------------------------------------------------------
# Exception Handeling added for checksum / string 
# -----------------------------------------------------------------------
#-----------------------------------------------------------------------
vfactor = 100.0/32768   # Volts
vrfactor = 99.667/32768 # Volts
ifactor = 79.16/32768   # Amps
ahfactor = 0.1          # Amp Hours (basically div by 10)
pofactor = 989.5/65536  # Watts
ohmfactor = 1.263/32768 # Ohms
perfactor = 100/256     # percent

nameOffset   = 0  # Offset in List for variable's name string
scalerOffset = 1  # Offset in List for scaler factor value
unitsOffset  = 2  # Offset in List for units of scale factor

StnName = 0       # Offset in Station info List for name string
StnIP = 1         # Offset in Station info List for IP address
StnPort = 2       # Offset in Station info List for Port Number

# Charge State Values... see RRD charts for example/explanations...
PChrgState = ["START",
              "NIGHT_CHECK",
  	      "DISCONNECT",
 	      "NIGHT",
	      "FAULT",
	      "BULK_CHARGE",
	      "ABSORPTION",
	      "FLOAT",
	      "EQUALIZE"]

# Charge State with load
PLoadState = ["START",
              "LOAD_ON",
 	      "LVD_WARNING",
	      "LVD",
              "FAULT",
  	      "DISCONNECT"]

# LED State Values
PLedState = ["LED_START",
             "LED_START2",
             "LED_BRANCH",
             "EQUALIZE (FAST GREEN BLINK)",
             "FLOAT (SLOW GREEN BLINK)",
             "ABSORPTION (GREEN BLINK, 1HZ)",
             "GREEN_LED",
             "UNDEFINED",
             "YELLOW_LED",
             "UNDEFINED",
             "BLINK_RED_LED",
             "RED_LED",
             "R-Y-G ERROR",
             "R/Y-G ERROR",
             "R/G-Y ERROR",
             "R-Y ERROR (HTD)",
             "R-G ERROR (HVD)",
             "R/Y-G/Y ERROR",
             "G/Y/R ERROR",
             "G/Y/R x 2"]

# Array Fault identified by Self-Diagnostics (bit field)
#                      Name       bit=0      bit=1
PArryFault = [["Overcurrent ", "No Fault", "Fault"],
              ["FETs shorted", "No Fault", "Fault"],
              ["Software bug", "No Fault", "Fault"],
              ["Battery HVD ", "No Fault", "Fault"],
              ["Array HVD   ", "No Fault", "Fault"],
              ["EEPROM setting reset required ", "No Fault", "Fault"],
              ["RTS shorted ", "No Fault", "Fault"],
              ["RTS was valid now disconnected", "No Fault", "Fault"],
              ["Local temp. sensor failed     ", "No Fault", "Fault"],
              ["Fault 10    ", "No Fault", "Fault"],
              ["Fault 11    ", "No Fault", "Fault"],
              ["Fault 12    ", "No Fault", "Fault"],
              ["Fault 13    ", "No Fault", "Fault"],
              ["Fault 14    ", "No Fault", "Fault"],
              ["Fault 15    ", "No Fault", "Fault"],
              ["Fault 16    ", "No Fault", "Fault"]]

# Load Fault identified by self diagnostics (bit field)
#                      Name                 bit=0      bit=1
PLoadFault = [["External Short Circuit   ", "No Fault", "Fault"],
              ["Overcurrent              ", "No Fault", "Fault"],
              ["FETs shorted             ", "No Fault", "Fault"],
              ["Software bug             ", "No Fault", "Fault"],
              ["HVD                      ", "No Fault", "Fault"],
              ["Heatsink over-temperature", "No Fault", "Fault"],
              ["EEPROM setting reset required ", "No Fault", "Fault"],
              ["Fault 8                  ", "No Fault", "Fault"]]

# Dip Switch settings (bit field)
# ... 4 position dip switch. 
# ... PDipSwitch[0][0] - Switch 1 Name string
# ... PDipSwitch[0][1] - Switch 1, '0' (off) value string
# ... PDipSwitch[0][0] - Switch 1, '1' (on) value string
# ... PDipSwitch[1][0] - Switch 2 Name string
# ... PDipSwitch[1][1] - Switch 2, '0' (off) value string
# ... PDipSwitch[1][0] - Switch 2, '1' (on) value string
dSwON = 2  # offset for switch ON state message
dSwOFF = 1 # offset for switch OFF state message
dSwNAM = 0 # offset for switch name
#                dSwNAM               dSWOFF                 dSwON
PDipSwitch = [["Battery Type", "User Select Jumper", "Custom Battery Settings"],
              ["LVD / LVR   ", "11.5V / 12.6V", "Custom Load Settings"],
              ["Equalize    ", "Disabled", "Enabled"],
              ["Comm Select ", "Meterbus", "MODBUS"]]



# Create name / scale factor lists / units
# These items are order dependent. The message list index is used
# as an index to this list. This list is ordered and needs to 
# be contigious!
#
# In order to scale and/or decode items the Scale Factor field is used
# to indicate what kind of items it is. Right now the following values
# are used to 'steer' the decoding / scaling process.
#
# Key to Scaler Field -
#  ' 1': The item is already in the proper format, no scaling necessary
#
#  '-1': Use the list named in the Units field to process State values
#      and the actual value of the param as the index to that list.
#           [Name String,  -1, "Name of List to use State Decode"]
#
#  '-2': Use the list named in the Units field to process bit encoded
#      information. Pass the param value to 'bitdecode' function for
#      processing.
#           [Name String,  -2, "Name of List to use Bit Decode"]
#
#  '-3': Indicates the param is the upper word of a 32/24 value (_HI).
#      Use this value plus the next param to form the Long integer.
#      Scale factor is stored in _HI 'unitsOffset' (Units) position
#      Units string is stored in _LO 'unitsOffset' (Units) position 
#           [Name String,  -3, Scale Factor]
#           [Name String,  -4, Units String]
#
#  '-4': Indicates the param is part of a Long integer (see -3 above)
#      and ignore processing
#
#  All other value are considered valid scale factors
#
#           [Name String,  Scale Factor, Units String]
# --------------------------------------------------------
PStatLst = [["Adc_vb_f", vfactor, "V"],
            ["Adc_va_f", vfactor, "V"],
            ["Adc_vl_f", vfactor, "V"],
	    ["Adc_ic_f", ifactor, "A"],
	    ["Adc_il_f", ifactor, "A"],
            ["T_hs", 1, "deg C"],
            ["T_batt", 1, "deg C"],
            ["T_amb", 1, "deg C"],
            ["T_rts", 1, "deg C"],
            ["Charge_State", -1, PChrgState],
            ["Array_Fault", -2, PArryFault],
            ["Vb_f", vfactor, "V"],
            ["Vb_ref", vrfactor, "V"],
            ["Ahc_r_HI", -3, ahfactor],
            ["Ahc_r_LO", -4, "Ah"],
            ["Ahc_t_HI", -3, ahfactor],
            ["Ahc_t_LO", -4, "Ah"],
            ["KWhc", ahfactor, "Ah"],
            ["Load_State", -1, PLoadState],
            ["Load_Fault", -2, PLoadFault],
            ["V_lvd", vfactor, "V"],
            ["Ahl_r_HI", -3, ahfactor],
            ["Ahl_r_LO", -4, "Ah"],
            ["Ahl_t_HI", -3, ahfactor],
            ["Ahl_t_LO", -4, "Ah"],
            ["Hourmeter_HI", -3, 1],
            ["Hourmeter_LO", -4, "Hours"],
            ["Alarm_HI", 1, "(bit field hi)"],
            ["Alarm_LO", 1, "(bit field lo)"],
            ["Dip_Switch", -2, PDipSwitch],
            ["LED_State", -1, PLedState],
            ["Power_out", pofactor, "W"],
            ["Sweep_Vmp", vfactor, "V"],
            ["Sweep_Pmax", pofactor, "W"],
            ["Sweep_Voc", vfactor, "V"],
            ["Vb_min_daily", vfactor, "V"],
            ["Vb_max_daily", vfactor, "V"],
            ["Ahc_daily", ahfactor, "Ah"],
            ["Ahl_daily", ahfactor, "Ah"],
            ["Array_Fault_daily", 1, "(bit field)"],
            ["Load_Fault_daily", 1, "(bit field)"],
            ["Alarm_HI_daily", 1, "(bit field hi)"],
            ["Alarm_LO_daily", 1, "(bit field lo)"],
            ["Vb_min", vfactor, "V"],
            ["Vb_max", vfactor, "V"]]

# Logged Data Record Message variable names and scale factors
PLogLst = [["hourmeter", 1, "Hours"],
           ["alarm_daily", 1, "(bit field)"],
           ["Vb_min_daily", vfactor, "V"],
           ["Vb_max_daily", vfactor, "V"],
           ["Ahc_daily", ahfactor, "Ah"],
           ["Ahl_daily", ahfactor, "Ah"],
           ["array_Fault_daily", 1, "(bit field)"],
           ["load_Fault_daily",1, "(bit field)"],
           ["Va_max_daily", vfactor, "V"],
           ["Time_ab_daily", 1, "Min"],
           ["Time_eq_daily", 1, "Min"],
           ["Time_fl_daily", 1, "Min"],
           ["reserved1", 1, " "],
           ["reserved2", 1, " "],
           ["reserved3", 1, " "]]

#these globals need to be defined.
params = None
data = None

import time
import socket
import os
import rrdtool
import sys

#added to handle a bad checksum beteen remote string and recieved string.
#make note and move to the next station, then try again.
#if you get to many,comment out the station in the station file... #stationlist....
class BadChecksum(Exception):
  pass

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# ------------ Start of Various Functions Definitions ---------------
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# ===================================================================
# calculate and returns the XOR checksum for pass string
# ------------------------------------------------------
# ...Assumes string starts with a '$' and it is not included
# ...in the checksum calculation.
# ===================================================================
def checksum(d):
  csum = 0
  dend = d.find('*')
  for x in d[1:dend]:
    csum ^= ord(x)
  return csum
# ... End checksum Function

# ===================================================================
# message send function
# ---------------------
#  returns the number chars sent
# ===================================================================
def mysend(sock, msg,  StationName):
    totalsent = 0
    #Exception handeling for send sockets.
    try:
        while totalsent < len(msg):
            sent = sock.send(msg[totalsent:])
            totalsent = totalsent + sent
    except (socket.timeout, socket.error) as e:
        print 'Station %s send error: %s' % (StationName, e)
        raise
    return totalsent
# ... End mysend Function ...

# ===================================================================
# data string recieve function
# ----------------------------
# Loops to get data from addressed socket either until the buffer
# is filled or the end of message. All these chunks are then joined
# and the new string is returned
# ===================================================================
def myreceive(sock, buflen,  StationName):
    chunks = []
    bytes_recd = 0
    #Exception handling for recieve sockets.
    try:
        while bytes_recd < buflen:
            chunk = sock.recv(min(buflen - bytes_recd, 2048))
            chunks.append(chunk)
            if chunk.find("\r\n") > 0:
              break
            bytes_recd = bytes_recd + len(chunk)
    except (socket.timeout, socket.error) as e:
        print 'Station %s receive error: %s' % (StationName, e)
        raise
    return ''.join(chunks)

#New CSV format for output/cronlog
formatCSV = '%s,%.2f,%s,'

#the doFunctions print the output to stdio... redirect as needed.

# ===================================================================
# Function to parse out and display battery voltage from battery voltage
# status message 
# ===================================================================
def doVbattery(params):
    sf = int(params[0])*PStatLst[0][scalerOffset]
    ns = PStatLst[0][nameOffset]
    units = PStatLst[0][unitsOffset]
# Origninal print statement
#    print format % (20, 'Battery Voltage', 4, ' 9', 12, ns, 8, sf, 10, ' '+units)
# New CSV formatted print statement for output/cronlog.
    print formatCSV % ('VBatt',sf,''+units), 
# ... End doVbattery Function ...

# ===================================================================
# Function to parse out and display array voltage from array voltage
# status message 
# ===================================================================    
def doVarray(params):
    sf = int(params[1])*PStatLst[1][scalerOffset]
    ns = PStatLst[1][nameOffset]
    units = PStatLst[1][unitsOffset]
#    print format % (20, 'Array Voltage', 4, '10', 12, ns, 8, sf, 10, ' '+units)    
# ... End doVarray Function ...

# ===================================================================
# Function to parse out and display load voltate from voltage
# status message 
# ===========================doShortScan========================================    
def doVload(params):
    sf = int(params[2])*PStatLst[2][scalerOffset]
    ns = PStatLst[2][nameOffset]
    units = PStatLst[2][unitsOffset]
#    print format % (20, 'Load Voltage', 4, '11', 12, ns, 8, sf, 10, ' '+units) 
# ... End doVload Function ...

# ===================================================================
# Function to parse out and display load current from current
# status message 
# ===================================================================
def doLoadCurrent(params):
  sf = int(params[4])*PStatLst[4][scalerOffset]
  ns = PStatLst[4][nameOffset]
  units = PStatLst[4][unitsOffset]
#  print format % (20, 'Load Current', 4, '13', 12, ns, 8, sf, 10, ' '+units)
# ... End doLoadCurrent Function ...

# ===================================================================
# Function to parse out and display load current from current
# status message 
# ===================================================================
def doChargingCurrent(params):
  sf = int(params[3])*PStatLst[3][scalerOffset]
  ns = PStatLst[3][nameOffset]
  units = PStatLst[3][unitsOffset]
#  print format % (20, 'Charging Current', 4, '12', 12, ns, 8, sf, 10, ' '+units)
# ... End doChargingCurrent Function ...


t_format  = '%-*s%-*s%-*s%*.2f%-*s%s%.1f%s'
# ===================================================================
# Function to parse out and display heatsink temperature from heatsink temperature
# status message 
# ===================================================================
def doTempheatsink(params):
  sf = int(params[5])*PStatLst[5][scalerOffset]
  sf1 = int(params[5])*1.8 + 32
  ns = PStatLst[5][nameOffset]
  units = PStatLst[5][unitsOffset]
#  print t_format % (20, 'Heatsink Temp', 4, '14', 12, ns, 8, sf, 6, ' '+units, ' (', sf1, 'F)')
# ... End doTempheatsink Function ...
    
# ===================================================================
# Function to parse out and display battery temperature IF probe connected! from battery temperature
# status message ambient if rts not connected.
# ===================================================================    
def doTempBattery(params):
  sf = int(params[6])*PStatLst[6][scalerOffset]
  sf1 = int(params[6])*1.8 + 32
  ns = PStatLst[6][nameOffset]
  units = PStatLst[6][unitsOffset]
#  print t_format % (20, 'Battery Temp', 4, '15', 12, ns, 8, sf, 6, ' '+units, ' (', sf1, 'F)')
# ... End doTempBattery Function ...

# ===================================================================
# Function to parse out and display ambient temperature from ambient
# temp from current status message 
# ===================================================================
def doTempAmbient(params):
  sf = int(params[7])*PStatLst[7][scalerOffset]
  sf1 = int(params[7])*1.8 + 32
  ns = PStatLst[7][nameOffset]
  units = PStatLst[7][unitsOffset]
#  print t_format % (20, 'Ambient Temp', 4, '16', 12, ns, 8, sf, 6, ' '+units, ' (', sf1, 'F)')
# ... End doTempAmbient Function ...

# ===================================================================
# Function to parse out and display rts temperature sensor
# status message. 0x80 if not connected.
# ===================================================================
def doTemprts(params):
  sf = int(params[8])*PStatLst[8][scalerOffset]
  sf1 = int(params[8])*1.8 + 32
  ns = PStatLst[8][nameOffset]
  units = PStatLst[8][unitsOffset]
#  print t_format % (20, 'RTS Temp', 4, '17', 12, ns, 8, sf, 6, ' '+units, ' (', sf1, 'F)')
# ... End doTemprts Function ...

# ===================================================================
# Function to parse out and display load current from current
# status message 
# Charge State Values
# PChrgState = ["START",
#              "NIGHT_CHECK",
#              "DISCONNECT",
#              "NIGHT",
#              "FAULT",
#              "BULK_CHARGE",
#              "ABSORPTION",
#              "FLOAT",
#              "EQUALIZE"]
# ===================================================================
def doChargeState(params):
  sf = int(params[9])                # grab raw value
  ns = PStatLst[9][nameOffset]
  # test if 'sf' gives a valid index for the PChrgState list
  # 0 - 8
  if (sf < 0) or (sf > 8):
    print 'invalid index into ChargeState list!!!'
    return
  units = (PStatLst[9][unitsOffset])[sf] # index list with value
#  print format % (20, 'Charge State', 4, '18', 12, ns, 8, sf, 10, ' '+units)
  if sf==0:
    print '%s,' % ('ChargeState,START'),#don't forget comma's to prevent newlines.
  elif sf==1: 
    print '%s,' % ('ChargeState,NIGHT_CHECK'), 
  elif sf==2:
    print '%s,' % ('ChargeState,DISCONNECT'),     
  elif sf==3: 
    print '%s,' % ('ChargeState,NIGHT'),     
  elif sf==4:
    print '%s,' % ('ChargeState,FAULT'), 
  elif sf==5: 
    print '%s,' % ('ChargeState,BULK_CHARGE'), 
  elif sf==6: 
    print '%s,' % ('ChargeState,ABSORPTION'),     
  elif sf==7:
    print '%s,' % ('ChargeState,FLOAT'),    
  elif sf==8: 
    print '%s,' % ('ChargeState,EQUALIZE'),  
# ... End doChargeState Function ...

# ===================================================================
# Function to parse out and display load state
# status message 
# Load State with load
# PLoadState = ["START",
#                "LOAD_ON",
#                "LVD_WARNING",
#                "LVD",
#                "FAULT",
#                "DISCONNECT"]
# ===================================================================
def doLoadState(params):
  sf = int(params[18])                # grab raw value
  ns = PStatLst[18][nameOffset]
  # test if 'sf' gives a valid index for the PLoadState list
  # 0 - 5
  if (sf < 0) or (sf > 5):
    print 'invalid index into LoadState list!!!'
    return
  units = (PStatLst[18][unitsOffset])[sf] # index list with value
#Original print
#  print format % (20, 'Load State', 4, '27', 12, ns, 8, sf, 10, ' '+units)
#===========================New CSV print===================================================== 
# This block is for putting the LoadState int he print / cron file. Should the RRD insert miss
# the LVD_WARNING, we can look to the log to get an idea of what happend before station quit.
  if sf==0:
    print '%s,' % ('LoadState,START'),#don't for get comma's to prevent newlines.
  elif sf==1: 
    print '%s,' % ('LoadState,LOAD_ON'),
  elif sf==2:
    print '%s,' % ('LoadState,LVD_WARNING'),    
  elif sf==3: 
    print '%s,' % ('LoadState,LVD'),    
  elif sf==4:
    print '%s,' % ('LoadState,FAULT'),    
  elif sf==5: 
    print '%s,' % ('LoadState,DISCONNECT'),   
 # else:
  #  continue
# ... End doLoadState Function ...

# ===================================================================
# Function to parse out and display load current compensated LVD voltage
# status message 
# ===================================================================
#Load current comensated LVD voltage   
def doLVDVoltage(params):
  sf = int(params[20])*PStatLst[20][scalerOffset]
  ns = PStatLst[20][nameOffset]
  units = PStatLst[20][unitsOffset]
#  print format % (20, 'LVD Voltage', 4, '29', 12, ns, 8, sf, 10, ' '+units)
  print formatCSV % ('Vlvd',sf,''+units), 
# ... End doLVDVoltage Function ...

# ===================================================================
# Function to parse out and display Vbatt - load current compensated LVD voltage
# status message aka Vdiff
# ===================================================================
#Load current comensated LVD voltage   
def doVdiff(params):
  sf1 = int(params[0])*PStatLst[0][scalerOffset]
  ns1 = PStatLst[0][nameOffset]
  units1 = PStatLst[0][unitsOffset]
  sf2 = int(params[20])*PStatLst[20][scalerOffset]
  ns2 = PStatLst[20][nameOffset]
  units2 = PStatLst[20][unitsOffset]
  Vdiff=sf1-sf2
  print formatCSV % ('Vdiff',Vdiff,''+units2), 
# ... End doVdiff Function ...
# ===================================================================
# Function to do the whole tamale. Get a status record from the 
# selected station. An integer is used to indicate the station to 
# query and the station table/file is used to get the actural name, 
# IP address and port.
# ===================================================================
def doShortScan(s,  StationName):
  global params, data
  # ===================================================================
  # Retrieve a status record from MPPT/Radio 
  # ----------------------------------------
  #  Send a request. This complete status record is place in "data" string.
  #  ****NOTE! Cell modems do not process any request over the serial port, T, R, E.....
  #  Freewave radio's do... All translators are defaulted to T mode
  #  and will reset to T mode. If you connect directly with a PC,
  #  try to remember to put the translator back into T mode please. 
  # ===================================================================
  x = mysend(s, 'R\r',  StationName) # send request for status data
  data = myreceive(s, 1024,  StationName)

  # ===================================================================
  # Prepare "data" string for splitting into components
  # ---------------------------------------------------
  # 1) Find end of message (start of checksum string) - 'eod'
  # 2) Retrieve the strings checksum - 'dchksum'
  # 3) The "data" string is then split and assigned to "parama" list
  #    (splitting using ',' delimiters and not including checksum)
  # 4) Remove the header string from the params list
  #    by POPPING it - 'dathdr'
  # 5) Remove the firmware revision string from the params list
  #    by POPPING it too - 'fwrev'
  # 6) The cleaned up "params" list is then used for the rest of the
  #    script
  # ===================================================================
  eod = data.find('*')
  dchksum = data[eod+1:-2]        # get the checksum value, no *, no CRLF

  # Exception for corrupted string.
  # If the checksum's do not match, return from the call to doShortScan and try again.
  # If they do match print it for debugging....remove later?
  #print 'string chksum: ', dchksum , ' - ',
  #print 'calc chksum: %0X' % (checksum(data)),   
  if (int(dchksum, 16)!=checksum(data)):
    print 'CHECKSUM MISMATCH %s,%0X' %(dchksum, checksum(data))
    raise BadChecksum
  #else:  
   # print 'string chksum: ', dchksum , ' - ',
   # print 'calc chksum: %0X' % (checksum(data)), 
  
  params = data[:eod].split(',')  # make a list out of the CSV string from translator
  dathdr = params.pop(0)          # get and remove the data header string
  fwrev = params.pop(0)           # get and remove the fw revision string

  #-----------------------------------------------------------------------------------------------------------------
  #CSV format for output header to log. Created to make cronlog easy to read with many stations. 
  #Can be imported into spread sheet for quick viewing....
  #Format of string is StationName,mm/dd/yyyy,hh:mm:ss,THE COMMA AT THE END OF THIS STATEMENT REMOVES THE NEWLINE!
  #So when you call the values you want to print, they are concatinated to the string to keep things pretty.
  #Pay special care to the comma's in the new CSV format print statements. Especially if you revert back to the original!
  #-----------------------------------------------------------------------------------------------------------------
  
#format StationName,mm/dd/yyyy,hh:mm:ss,  
  lt = time.localtime()
  print '%s,%d/%d/%d,%02d:%02d:%02d,' % (StationName, lt.tm_mon, lt.tm_mday, lt.tm_year, lt.tm_hour, lt.tm_min, lt.tm_sec ), 
 

#----------------------------------------------------------------------
  # ---------------
  #Load State 
  #Moved here so CSV would show states, especially LVD_WARNING first in string after date-time stamp.
  #------------------
  doLoadState(params)
  # Battery Voltage
  # ---------------
  doVbattery(params)
  # ---------------
  # Array Voltage
  # ---------------
  doVarray(params)
  # ---------------
  # Load Voltage
  # ---------------
  doVload(params)
  # -----------------
  # Charging Current
  # -----------------
  doChargingCurrent(params)
  # ---------------
  # Load Current
  # ---------------
  doLoadCurrent(params)
  # ---------------------
  # Various Temperatures
  # ---------------------
  doTempheatsink(params)
  doTempBattery(params)
  doTempAmbient(params)
  doTemprts(params)  # RTS = Remote Temp Sensor
  # -----------------------------------------------------
  # Low Voltage Disconnect Setpoint, current compensated
  # -----------------------------------------------------
  doLVDVoltage(params)
  #--------------------------
  # Print Vdiff=VBatt-Vlvd
  #--------------------------
  doVdiff(params)
  # -------------------------
  # Various State Conditions
  # -------------------------
  doChargeState(params)
  
  # ------------------------------------------------------------------
  # Return translator to Timed 
  # Message Mode before Exiting
  # ------------------------------------------------------------------
  x = mysend(s, 'T\r', StationName)
  #print "Returning back to timed mode"

# ... End doShortScan Function ...


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# ------------------ Start of Main Script ---------------------------
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
while True:#Always on Loop to cycle.
    cycle_start = time.time()

    #for x in range(1000):
    #Put the output in a txt file.
    sys.stdout=open("Insert8.3.log", "a+")
    # declare the path to the input file
    #sfpath = ("C:\\Users\\Dan\\Desktop\\Radio Modbus Stuff")
    sfpath = ("/home/mbiundo/Desktop/MCSOH/RRDTool/Insert8/")
    # open input file for reading using tfpath above
    #stationfile = open(sfpath + "//" + "//StationList.txt", "r")
    stationfile = open(sfpath  + "/StationList.txt", "r")
    #=============================================================================
    # read the file line by line until EOF
    # File line entry  example:
    #  Station Name, IP Address, Port Number<CR><LF> (newline)
    # Comma Separated Values (CSV) followed by a newline (CRLF)
    #=============================================================================
    
    while True:#Loop to cycle through the StationList.txt file.
        sfline = stationfile.readline()
        # strip off newline and create list of fields
        sfline = sfline.rstrip()
        if not sfline:
            break # exit loop if end of file (EOF)
        # convert CSV into a list
        sftext = sfline.split(",")
        # check for a commented out line
        if sfline[0] == '#':
            # OPTIONAL - print name of station that is being skipped (minus the #)
           print 'Skipping: ', (sftext[0][1:])
           continue # skip this iteration and go on to the next
        # make sure the list is three elements before continuing
        if len(sftext) < 3:
            break # exit loop at first sign of trouble
    
    
        StationName = sftext[0]
        StationIP = sftext[1]
        StationPort = int(sftext[2])
    
        # create a socket
        # 30 seconds worked well in testing for cell....
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
    
        # connect it to the IP address and Port number
        # Use StationList for IP and Port
        host = StationIP
        port = StationPort
        #Comm's Exceptions added to make errors more informative
        try:
            try:
                s.connect((host, port))
            except (socket.timeout, socket.error, socket.gaierror) as e:
                print 'Station %s (%s:%s) connection error: %s' % (StationName, host, port, e)
                raise
            for x in range(1):  # stress test by setting > 1
                #print '%s,%s' % (host, port)
                # ===================================================================
                # Function to do the whole tamale. Get a status record from the 
                # selected station. All the info is placed in the Global list
                # called "params".
                # ===================================================================
                start = time.time()
                doShortScan(s, StationName)
                #Comm_Duration may be added to the RRD as well. It may be good to track and compare
                #between cell,LAN and Radio connectivity differences.
                Comm_Duration = time.time() - start
                #print 'Station: %s communication time: %.3f seconds' % (StationName,  comm_duration)
                print 'Comm_Duration, %.3f, seconds,' % (Comm_Duration) 
        except (socket.timeout, socket.error, socket.gaierror, BadChecksum):
            continue
    
    
        #--------------------- Partial example for RRDTOOL LAYOUT AND INSERT function--------------------
        #---------------------The RRDTool Insert function must match the RRD database layout.
        #RRDTool database layout for mcsoh2.rrd
        # DS:Adc_vb_f:GAUGE:600:0:65535 \   params[0]
        # DS:Adc_va_f:GAUGE:600:0:65535 \   params[1]
        # DS:Adc_vl_f:GAUGE:600:0:65535 \   params[2]
        # DS:Adc_ic_f:GAUGE:600:0:65535 \   params[3]
        # DS:Adc_il_f:GAUGE:600:0:65535 \   params[4]
        # DS:T_hs:GAUGE:600:-128:127 \      params[5]
        # DS:T_batt:GAUGE:600:-127:127 \    params[6]
        # DS:T_amb:GAUGE:600:-127:127 \     params[7]
        # DS:T_rts:GAUGE:600:-127:127 \     params[8]
        # DS:Charge_State:GAUGE:600:0:8 \   params[9]
        # DS:load_state:GAUGE:600:0:6 \     params[18]
        # DS:V_lvd:GAUGE:600:0:65535 \      params[20]
    
        #====================================================================================================
        #    45 Internal register entries from MPPT into RRD Database.
        #    You can reference Morningstar's SunSaver MPPT MODBUS Specifcation V10, 14 July 2010 for details.
        #    Append additional values to the end of the %(int params[]) list below... Just make sure the
        #    additions identical in the RRD db and script that creates it.
        #====================================================================================================
        ret = rrdtool.update('/home/mbiundo/Desktop/MCSOH/RRDTool/Insert8/'+StationName+'.rrd','N:\
        %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:\
        %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:\
        %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:\
        %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:\
        %d:%d:%d:%d:%d:%f'\
        % (int(params[0]),int(params[1]) ,int(params[2]) ,int(params[3]) ,int(params[4]) ,int(params[5]) ,\
        int(params[6]) ,int(params[7]) ,int(params[8]) , int (params[9]), int (params[10]) , \
        int(params[11]) ,int(params[12]) ,int(params[13]) , int (params[14]), int (params[15]) , \
        int(params[16]) ,int(params[17]) ,int(params[18]) , int (params[19]), int (params[20]) , \
        int(params[21]) ,int(params[22]) ,int(params[23]) , int (params[24]), int (params[25]) , \
        int(params[26]) ,int(params[27]) ,int(params[28]) , int (params[29]), int (params[30]) , \
        int(params[31]) ,int(params[32]) ,int(params[33]) , int (params[34]), int (params[35]) , \
        int(params[36]) ,int(params[37]) ,int(params[38]) , int (params[39]), int (params[40]) , \
        int(params[41]) ,int(params[42]) ,int(params[43]) , int (params[44]), Comm_Duration )); 
    
        if ret:
            print rrdtool.error()
        #======================================================================================================
        
        # -------------------
        # close out socket(s)
        # -------------------
        s.close()
    #== End Of File read loop =============================
    # close the station information input file
    stationfile.close()
       
    #clean up output...
    sys.stdout.flush()
    #Sleep time set typically the first max argument if it is 3 minutes or longer.    
    time.sleep(max(180, 60 - (time.time() - cycle_start)))    # sleep until time to start next cycle
# ... End of Script ...

