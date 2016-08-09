#!/bin/bash
rrdtool graph LCCR_currents_graph.png \
-w 785 -h 120 -a PNG \
--slope-mode \
--start -360000 --end now \
--font DEFAULT:7: \
--title "Station LCCR MPPT Solar Controller Data" \
--watermark "`date`" \
--vertical-label "Amps" \
--right-axis-label "Amps" \
--lower-limit -5 \
--right-axis 1:0 \
--color CANVAS#000000 \
--color FONT#FFFFFF \
--color BACK#000000 \
DEF:Adc_ic_f=LCCR_mppt.rrd:Adc_ic_f:AVERAGE \
DEF:Adc_il_f=LCCR_mppt.rrd:Adc_il_f:AVERAGE \
CDEF:Icharge=Adc_ic_f,79.16,32768,/,* \
CDEF:Iload=Adc_il_f,-79.16,32768,/,* \
COMMENT:"The Icharge values are of positive value,(shown on the +y axis). Iload are negative,(shown on the -y axis).\\l" \
AREA:Icharge#00ff00:"Icharge" \
GPRINT:Icharge:LAST:"Last\:%2.2lf" \
GPRINT:Icharge:AVERAGE:"Avg\:%2.2lf" \
GPRINT:Icharge:MAX:"Max\:%2.2lf" \
GPRINT:Icharge:MIN:"Min\:%2.2lf\n" \
AREA:Iload#ff0000:"Iload" \
GPRINT:Iload:LAST:"Last\:%2.2lf" \
GPRINT:Iload:AVERAGE:"Avg\:%2.2lf" \
GPRINT:Iload:MIN:"Max\:%2.2lf" \
GPRINT:Iload:MAX:"Min\:%2.2lf\n"



