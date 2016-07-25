# mcsoh
Power System State of Health from Morningstar MPPT-15L Solar Controller 
#---------------------------------------------------------------
# Marc Biundo 6/1/16 
# Version 8.3
# This program is desinged to facilitate communications with multiple Morningstar SunSaver MPPT Solar Controlers Remotely via TCP/IP.
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
# The convention for this program is to name the RRD Database as: StationName_mppt.rrd i.e. LCCR_mppt.rrd
# future versions that track other SOH data will use a similar convention. This will help with graphing from multiple RRD databases...
# A ten year database is approximatly 1M bytes in size. And since it is a ring, it will overwrite in 10 years.
#
