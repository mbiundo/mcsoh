#!/bin/bash 
rrdtool graph CommDura_graph.png \
-w 785 -h 120 -a PNG \
--slope-mode \
--start -864000 --end now \
--font DEFAULT:7: \
--title "Round Trip Communication Duration" \
--watermark "`date`" \
--vertical-label "Seconds" \
--right-axis-label "Seconds" \
--lower-limit 0 \
--right-axis 1:0 \
--color CANVAS#000000 \
DEF:CD0=MARC_mppt.rrd:Comm_Duration:AVERAGE \
CDEF:MARC_Comm_Duration0=CD0,1,*  \
LINE1:MARC_Comm_Duration0#ff0000:"MARC_mppt Communications Duration in Seconds" \
GPRINT:MARC_Comm_Duration0:LAST:"Last\:%2.2lf" \
GPRINT:MARC_Comm_Duration0:AVERAGE:"Avg\:%2.2lf" \
GPRINT:MARC_Comm_Duration0:MAX:"Max\:%2.2lf" \
GPRINT:MARC_Comm_Duration0:MIN:"Min\:%2.2lf\n" \
DEF:CD1=LCCR_mppt.rrd:Comm_Duration:AVERAGE \
CDEF:LCCR_Comm_Duration1=CD1,1,*  \
LINE1:LCCR_Comm_Duration1#00ff00:"LCCR_mppt Communications Duration in Seconds" \
GPRINT:LCCR_Comm_Duration1:LAST:"Last\:%2.2lf" \
GPRINT:LCCR_Comm_Duration1:AVERAGE:"Avg\:%2.2lf" \
GPRINT:LCCR_Comm_Duration1:MAX:"Max\:%2.2lf" \
GPRINT:LCCR_Comm_Duration1:MIN:"Min\:%2.2lf\n" \
DEF:CD2=FISH_mppt.rrd:Comm_Duration:AVERAGE \
CDEF:FISH_Comm_Duration2=CD2,1,*  \
LINE1:FISH_Comm_Duration2#000ff0:"FISH_mppt Communications Duration in Seconds" \
GPRINT:FISH_Comm_Duration2:LAST:"Last\:%2.2lf" \
GPRINT:FISH_Comm_Duration2:AVERAGE:"Avg\:%2.2lf" \
GPRINT:FISH_Comm_Duration2:MAX:"Max\:%2.2lf" \
GPRINT:FISH_Comm_Duration2:MIN:"Min\:%2.2lf\n"
