#!/bin/bash     
rrdtool graph LCCR_ChargeState_graph.png \
-w 785 -h 120 -a PNG \
--slope-mode \
--start -360000 --end now \
--font DEFAULT:7: \
--title "Station LCCR MPPT Solar Controller Data" \
--watermark "`date`" \
--vertical-label "Charge States" \
--right-axis-label "Charge States" \
--lower-limit 0 \
--right-axis 1:0 \
--color CANVAS#000000 \
--color FONT#FFFFFF \
--color BACK#000000 \
DEF:Charge_State=LCCR_mppt.rrd:Charge_State:AVERAGE \
COMMENT:"BULK CHARGE-The battery is not at 100% state of charge and battery voltage has not yet charged to the\n" \
COMMENT:"Absorption voltage setpoint. The controller will deliver 100% of available solar power to recharge\n" \
COMMENT:"the battery.\n" \
COMMENT:"------------------------------------------------------------------------------------------------------------------------\n" \
COMMENT:"ABSORPTION-When the battery has recharged to the Absorption voltage setpoint, constant-voltage regulation\n" \
COMMENT:"is used to maintain battery voltage at the Absorption setpoint. This prevents heating and excessive battery gassing.\n" \
COMMENT:"The battery is allowed to come to full state of charge at the Absorption voltage setpoint.\n" \
COMMENT:"The battery must remain in the Absorption charging stage for a cumulative 120-150 minutes, depending on battery type,\n" \
COMMENT:"before transition to the Float stage will occur. However, Absorption time will be extended by 30 minutes if the battery\n" \
COMMENT:"dicharges below 12.5 V the previous night. The Absorption setpoint is temperature compensated if the RTS is connected.\n" \
COMMENT:"------------------------------------------------------------------------------------------------------------------------\n" \
COMMENT:"FLOAT-After the battery is fully charged in the Absorption stage, the MPPT reduces the battery voltage to the Float\n" \
COMMENT:"voltage setpoint. When the battery is fully recharged, there can be no more chemical reactions and all the charging\n" \
COMMENT:"current is turned into heat and gassing. The float stage provides a very low rate of maintenance charging while reducing\n" \
COMMENT:"the heating and gassing of a fully charged battery. The purpose of Float is to protect the battery from long-term\n" \
COMMENT:"overcharge.\n" \
COMMENT:"Once in Float stage, loads can continue to draw power from the battery. In the event that the system load exceeds solar\n" \
COMMENT:"charge current, the controller will no longer be able to maintain the battery at the Float setpoint. Should the battery\n" \
COMMENT:"voltage remain below the Float setpoint for a cumulative 30 minutes, the controller will exit Float and retrun to Bulk.\n" \
COMMENT:"The Float setpoint is temperature compensated if the RTS is connected.\n" \
COMMENT:"------------------------------------------------------------------------------------------------------------------------\n" \
CDEF:CS=Charge_State \
CDEF:Start=CS,0,EQ,CS,0,IF \
AREA:Start#0099ff:"Start=0" \
CDEF:Night_Check=CS,1,EQ,CS,0,IF \
AREA:Night_Check#660066:"Night_Check=1" \
CDEF:Disconnect=CS,2,EQ,CS,0,IF \
AREA:Disconnect#990000:"Disconnect=2" \
CDEF:Night=CS,3,EQ,CS,0,IF \
AREA:Night#555555:"Night=3" \
CDEF:Fault=CS,4,EQ,CS,0,IF \
AREA:Fault#ff0000:"Fault=4" \
CDEF:Bulk_Charge=CS,5,EQ,CS,0,IF \
AREA:Bulk_Charge#ff9900:"Bulk_Charge=5" \
CDEF:Absorption=CS,6,EQ,CS,0,IF \
AREA:Absorption#ffff00:"Absorption=6" \
CDEF:Float=CS,7,EQ,CS,0,IF \
AREA:Float#00ff00:"Float=7" \
CDEF:Equalize=CS,8,EQ,CS,0,IF \
AREA:Equalize#ff00ff:"Equalize=8\n" \
GPRINT:CS:LAST:"Last\:%2.2lf\n" 
 


