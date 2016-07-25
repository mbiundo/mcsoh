#!/bin/bash 
rrdtool graph voltage_graph.png \
-w 785 -h 120 -a PNG \
--slope-mode \
--start -864000 --end now \
--font DEFAULT:7: \
--title "Station MARC MPPT Solar Controller Data" \
--watermark "`date`" \
--vertical-label "Volts" \
--right-axis-label "Volts" \
--lower-limit 0 \
--right-axis 1:0 \
--color CANVAS#000000 \
DEF:Adc_vb_f=MARC_mppt.rrd:Adc_vb_f:AVERAGE \
DEF:Adc_va_f=MARC_mppt.rrd:Adc_va_f:AVERAGE \
DEF:V_lvd=MARC_mppt.rrd:V_lvd:AVERAGE \
DEF:Load_State=MARC_mppt.rrd:Load_State:AVERAGE \
CDEF:LS=Load_State \
CDEF:START=LS,0,EQ,LS,0,IF \
CDEF:LOAD_ON=LS,1,EQ,LS,0,IF \
CDEF:LVD_WARNING=LS,2,EQ,LS,0,IF \
CDEF:Vbatt=Adc_vb_f,100,32768,/,* \
CDEF:Varray=Adc_va_f,100,32768,/,* \
CDEF:LVD=V_lvd,100,32768,/,* \
COMMENT:"The "LVD" voltage is a load current compensated, Low Voltage Disconnect.\\l" \
COMMENT:"This line is a constant set point, but may adjust based on loading.\\l" \
COMMENT:"The LVD Alarm will become visible(a yelow area), when Vbatt approaches/drops to LVD voltage.\:\l" \
LINE2:LVD#ff0000:"LVD" \
GPRINT:LVD:LAST:" Last\:%2.2lf\l" \
LINE2:Vbatt#ff00ff:"Vbatt" \
GPRINT:Vbatt:LAST:"Last\:%2.2lf" \
GPRINT:Vbatt:AVERAGE:"Avg\:%2.2lf" \
GPRINT:Vbatt:MAX:"Max\:%2.2lf" \
GPRINT:Vbatt:MIN:"Min\:%2.2lf\n" \
LINE2:Varray#0000ff:"Varray" \
GPRINT:Varray:LAST:"Last\:%2.2lf" \
GPRINT:Varray:AVERAGE:"Avg\:%2.2lf" \
GPRINT:Varray:MAX:"Max\:%2.2lf" \
GPRINT:Varray:MIN:"Min\:%2.2lf\n" \
AREA:LS#00ff00:"Load_State" \
GPRINT:LS:LAST:"Last\:%2.1lf\n" 
 
 

