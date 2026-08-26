10 rem -- c128 pong --
20 graphic 0:scnclr 0
30 color 0,1:color 4,1:color 5,7
40 gosub 1000
50 gosub 2000
60 gosub 3000
70 gosub 4000
80 end
1000 rem -- intro scherm --
1010 scnclr 0
1020 char 1,16,4,"pong"
1030 char 1,2,8,"speler 1: w = omhoog  s = omlaag"
1040 char 1,2,10,"speler 2: o = omhoog  l = omlaag"
1050 char 1,7,13,"eerst tot 5 punten wint"
1060 char 1,8,16,"druk een toets om te starten"
1070 vol 8:tempo 10
1080 play "v1o4t0u6cegcegc"
1090 getkey k$
1100 vol 0
1110 return
2000 rem -- sprites + rand bouwen --
2010 dim sb(63)
2020 for i=0 to 62:sb(i)=0:next i
2030 for r=0 to 7:sb(r*3+1)=255:next r
2040 s$=""
2050 for i=0 to 62:s$=s$+chr$(sb(i)):next i
2060 sprsav s$,1
2070 for i=0 to 62:sb(i)=0:next i
2080 for r=0 to 20:sb(r*3+1)=255:next r
2090 s$=""
2100 for i=0 to 62:s$=s$+chr$(sb(i)):next i
2110 sprsav s$,2
2120 sprsav s$,3
2130 sprite 1,1,7,0,0,0,0
2140 sprite 2,1,2,0,0,0,0
2150 sprite 3,1,8,0,0,0,0
2160 rem rand-string (40 blokken)
2170 bs$=""
2180 for i=1 to 40:bs$=bs$+chr$(160):next i
2190 return
3000 rem -- spel --
3010 scnclr 0
3020 color 1,8:char 1,0,6,bs$
3030 char 1,0,19,bs$:color 1,7
3040 bx=160:by=100
3050 px=30:py=90
3060 ax=290:ay=90
3070 dx=5:dy=3
3080 ps=0:cs=0
3090 tb=50:bb=150
3100 gosub 6000
3110 movspr 1,bx,by
3120 movspr 2,px,py
3130 movspr 3,ax,ay
3140 do
3150 get k$
3160 if k$="w" then py=py-4
3170 if k$="s" then py=py+4
3180 if k$="o" then ay=ay-4
3190 if k$="l" then ay=ay+4
3200 if py<tb then py=tb
3210 if py>130 then py=130
3220 if ay<tb then ay=tb
3230 if ay>130 then ay=130
3240 bx=bx+dx:by=by+dy
3250 if by<tb then by=tb:dy=-dy
3260 if by>bb then by=bb:dy=-dy
3270 rem bat links (speler 1)
3280 if bx<=px+8 and by>=py-7 and by<=py+20 then dx=5
3290 rem bat rechts (speler 2)
3300 if bx>=ax-8 and by>=ay-7 and by<=ay+20 then dx=-5
3310 if bx<10 then cs=cs+1:gosub 5000
3320 if bx>310 then ps=ps+1:gosub 5000
3330 movspr 1,bx,by
3340 movspr 2,px,py
3350 movspr 3,ax,ay
3360 if ps>=5 then exit
3370 if cs>=5 then exit
3380 loop
3390 vol 0
3400 sprite 1,0
3410 sprite 2,0
3420 sprite 3,0
3430 return
4000 rem -- einde --
4010 scnclr 0
4020 if ps>=5 then char 1,14,10,"speler 1 wint!"
4030 if cs>=5 then char 1,14,10,"speler 2 wint!"
4040 vol 8:tempo 10
4050 if ps>=5 then play "v1o4t0u6cegcegcegc"
4060 if cs>=5 then play "v1o3t0u6cgcfcecgc"
4070 char 1,12,15,"druk een toets"
4080 getkey k$
4090 vol 0
4100 return
5000 rem -- punt gescoord --
5010 gosub 6000
5020 vol 6:sound 1,8192,20
5030 bx=160:by=100
5040 dx=-dx:dy=3
5050 movspr 1,bx,by
5060 return
6000 rem -- score tonen --
6010 char 1,2,0,"p1:"
6020 char 1,6,0,str$(ps)
6030 char 1,30,0,"p2:"
6040 char 1,34,0,str$(cs)
6050 return