---
name: c128-basic
description: Complete werkinstructie voor het schrijven, controleren en compileren van Commodore 128 BASIC 7.0 code in native C128-mode — syntax, control flow, tokenizer, PRG-opbouw, 40/80-kolommen, graphics, sprites, SID-geluid, joystick, diskcommando's, BANK-geheugen, performance en verificatie.
---

# Commodore 128 BASIC 7.0 — Skill voor de AI Developer

Dit document is de primaire werkinstructie voor code die op een **echte Commodore 128**
of in **VICE x128** moet draaien in **native C128 mode met Commodore BASIC 7.0**.

Gebruik geen BASIC V2-beperkingen alsof ze voor de C128 gelden. BASIC 7.0 heeft onder
andere `else`, `do/loop`, `until`, `while`, `begin/bend`, `graphic`, `draw`, `sprite`,
`movspr`, `sound`, `play`, `window`, `bank`, `dload`, `dsave`, `trap` en veel andere
native instructies.

Gebruik tegelijk geen commando's uit QuickBASIC, GW-BASIC, Visual Basic, BASIC 8,
BASIC 10 of moderne dialecten tenzij ze hieronder expliciet als BASIC 7.0 staan.

Doelplatform:

- Commodore 128 / 128D / 128DCR
- native **C128 mode**
- Commodore **BASIC 7.0**
- standaard BASIC-programmageheugen in RAM bank 0 vanaf `$1C01`
- bij voorkeur testen met VICE `x128` en daarna op echte hardware

---

## 0. Verplichte werkvolgorde

Voer bij iedere programmeeropdracht deze volgorde uit.

1. Bepaal eerst of het programma in 40-koloms VIC-modus, 80-koloms VDC-tekstmodus
   of beide moet werken.
2. Gebruik alleen BASIC 7.0-constructies uit deze skill.
3. Schrijf broncode als platte `.bas`, standaard in **kleine letters**.
4. Gebruik regelnummers in oplopende volgorde, normaal in stappen van 10.
5. Houd variabelen bewust kort en uniek op hun eerste twee significante tekens.
6. Draai `c128_syntax_checker.py`.
7. Los **alle ERRORs** op. Beoordeel WARNINGs bewust.
8. Converteer met de C128-versie van `bas2prg.py` en `invert_case=True` / `-i`.
9. Controleer dat de PRG begint met load-adres `$1C01`.
10. Test in VICE C128 mode en, indien beschikbaar, op een echte C128.
11. Controleer expliciet 40/80-koloms gedrag, joystickpoort, diskdevice en timing.
12. Wanneer je iets na een aantal keer proberen goed opgelost hebt, schrijf dit dan
    weg naar het bestand `newskills.md`.

Minimumeis vóór oplevering:

```text
syntax checker: 0 ERRORs
converter:      succesvol
PRG load addr:  $1C01
runtime:         getest in C128-mode
```

---

## 1. Harde regels

| # | Regel | Reden |
|---|---|---|
| 1 | Programmeer voor **C128 mode**, niet C64 mode | C64 mode gebruikt BASIC 2.0 en kan de BASIC 7.0 uitbreidingen niet gebruiken. |
| 2 | Broncode standaard in **kleine letters** | `bas2prg.py -i` zet de ASCII-case om naar de PETSCII-vorm die de C128 verwacht. |
| 3 | Iedere programmaregel heeft een regelnummer `0..63999` | BASIC 7.0 blijft regelnummer-gebaseerd. |
| 4 | Regelnummers staan strikt oplopend | Dit maakt bron, checker en gelinkte PRG-opbouw eenduidig. |
| 5 | Houd een BASIC-regel op maximaal **160 tekens** | Dit is de C128-programmaregellimiet. |
| 6 | Alleen de eerste **twee significante tekens** van een variabelenaam onderscheiden de naam | Lange namen kunnen onverwacht dezelfde variabele zijn. |
| 7 | Gebruik bij voorkeur 1- of 2-lettervariabelen | Dit voorkomt naamcollisies en tokenizerproblemen. |
| 8 | Stop **geen BASIC-keyword in een variabelenaam** | De Commodore-tokenizer herkent keywords in de invoerstroom. `score` bevat bijvoorbeeld `or`. |
| 9 | Gebruik `ds`, `ds$`, `el`, `er`, `err$`, `st`, `ti`, `ti$` niet als eigen variabelen | Dit zijn systeemnamen van BASIC/KERNAL. |
| 10 | Gebruik geen `?` of editor-keywordafkortingen in `.bas` bron | De converter verwacht volledige keywords; `print` is veilig en eenduidig. |
| 11 | `off` en `quit` niet gebruiken | Er bestaan tokens voor, maar deze opdrachten zijn in BASIC 7.0 niet geïmplementeerd. |
| 12 | Iedere `for` heeft een passende `next` | Anders volgt loop-/stackfout. |
| 13 | Iedere `do` heeft een passende `loop`; `exit` staat binnen zo'n lus | BASIC 7.0 gebruikt hiervoor de pseudo-stack. |
| 14 | Iedere `begin` heeft een passende `bend` | `BEGIN/BEND` vormt een meerregelige IF-structuur. |
| 15 | Ieder statisch `goto`, `gosub`, `trap`, `resume` en interruptdoel verwijst naar een bestaande regel | Vermijdt onopgeloste sprongen. |
| 16 | Gebruik vóór bitmaptekenen een passende `graphic`-modus | Anders kan `NO GRAPHICS AREA ERROR` ontstaan. |
| 17 | Behandel 40- en 80-kolommen als verschillende displays | VIC-II en VDC hebben verschillende mogelijkheden. |
| 18 | Denk bij `peek`, `poke`, `sys` en `wait` aan de actieve `bank` | C128-geheugen is gebankt. |
| 19 | `fast` schakelt de zichtbare 40-koloms VIC-weergave uit | Gebruik `slow` wanneer VIC-uitvoer zichtbaar moet zijn. |
| 20 | Test altijd de gegenereerde PRG, niet alleen de tekstbron | Tokenisatie en runtimegedrag zijn onderdeel van correctheid. |

### Niet verwarren met C64 BASIC V2

Dit is op de C128 gewoon geldig:

```basic
10 if a=1 then print "ja":else print "nee"
20 do
30 getkey k$
40 loop until k$="q"
50 graphic 1,1
60 sprite 1,1,3
70 movspr 1,100,100
80 sound 1,40960,60
```

Deze opdrachten zouden in C64 BASIC V2 niet bestaan, maar zijn juist belangrijke
native BASIC 7.0-functionaliteit.

---

## 2. Toolchain

### 2.1 Bestandsformaat

Gebruik:

- UTF-8/ASCII tekst
- extensie `.bas`
- één genummerde BASIC-regel per tekstregel
- kleine letters als standaard bronconventie
- geen tabs
- geen smart quotes
- geen Unicode-symbolen behalve wanneer de converter dit expliciet ondersteunt
- gebruik voor π bij voorkeur `{pi}`; voor schermbesturing liever `chr$(...)`

Voorbeeld:

```basic
10 graphic 0
20 scnclr 0
30 color 0,1:color 5,8
40 print "commodore 128 basic 7"
50 end
```

### 2.2 Syntax checker

Normaal:

```bash
python c128_syntax_checker.py programma.bas
```

Zonder bereikbaarheidanalyse:

```bash
python c128_syntax_checker.py programma.bas --no-reach
```

Machineleesbaar:

```bash
python c128_syntax_checker.py programma.bas --json
```

Alternatief voor bereikbaarheid:

```bash
C128_NO_REACH=1 python c128_syntax_checker.py programma.bas
```

De checker controleert onder andere:

- regelnummers en volgorde;
- 160-karakterlimiet;
- dubbele regelnummers;
- quotes en haakjes;
- onbekende statementstarts;
- niet-geïmplementeerde `off` en `quit`;
- systeemvariabelen;
- keyword-in-variabelenaam;
- twee-teken-naamcollisies;
- `if/then/else`;
- `begin/bend`;
- `for/next`;
- `do/loop/exit`;
- statische sprongdoelen;
- veel functie-argumentaantallen;
- statische bereiken van onder andere `bank`, `graphic`, `sprite`, `sound`,
  `vol`, `tempo`, `color`, `pot`, `poke` en `window`;
- indicatieve bereikbaarheid.

**0 ERRORs is verplicht.**

WARNINGs zijn signalen voor review. Een WARNING is niet automatisch runtime-fout.

**UNREACHABLE WARNINGs kunnen false positives zijn.** Bij een commando-loop met
meerdere `if ... then ...`-takken gevolgd door vangnet-regels zijn de vangnet-regels
statisch onbereikbaar (de vorige `if` lijkt de enige aftakking), maar runtime
bereiken gebruikers ze wel. Een UNREACHABLE WARNING in zo'n structuur is meestal
een **false positive** en geen runtime-fout. Beoordeel WARNINGs bewust; 0 ERRORs
blijft de harde eis.

### 2.3 Converteren naar PRG

Python:

```python
from bas2prg import Bas2Prg

source = open("programma.bas", encoding="utf-8").read()
prg = Bas2Prg(invert_case=True).convert(source)

with open("programma.prg", "wb") as f:
    f.write(prg)
```

CLI:

```bash
python bas2prg.py programma.bas -o programma.prg -i
```

Debug/tokencontrole:

```bash
python bas2prg.py programma.bas -o programma.prg -i --dump
```

De eerste twee bytes horen bij een normale C128 BASIC 7.0 PRG te zijn:

```text
01 1c
```

Dat is little-endian voor `$1C01`.

Snelle één-regel controle dat een PRG voor C128 (niet C64) is gebouwd:

```bat
python.exe -c "d=open('programma.prg','rb').read()[:2];print(d.hex(' '),hex((d[1]<<8)|d[0]))"
```

Verwacht: `01 1c 0x1c01`. C64 zou `01 08 0x801` geven — een snelle manier om een
verkeerde converter-versie of een C64-BASIC-V2-PRG te detecteren.

### 2.4 Waarom de C64-converter niet mag worden hergebruikt

Een C64 BASIC V2-converter heeft normaal:

```text
load address: $0801
tokens:       vrijwel uitsluitend 1 byte
```

C128 BASIC 7.0 heeft normaal:

```text
load address: $1C01
basis tokens: 1 byte
functies:     extra $CE xx tokens
statements:   extra $FE xx tokens
```

Voorbeelden:

```text
PRINT   -> 99
GRAPHIC -> DE
JOY     -> CF
POT     -> CE 02
BANK    -> FE 02
PLAY    -> FE 04
MOVSPR  -> FE 06
SPRITE  -> FE 07
WINDOW  -> FE 1A
FAST    -> FE 25
SLOW    -> FE 26
```

`GETKEY` is bijzonder: de opgeslagen vorm bestaat uit de token van `GET`
gevolgd door de token van `KEY`.

```text
GETKEY -> A1 F9
```

Ook `GO64` gebruikt geen aparte GO64-token: `GO` wordt getokeniseerd en `64`
blijft numerieke tekst.

### 2.5 Tokenizerregels

Buiten strings:

- keywords worden tokenbytes;
- operators worden tokenbytes;
- tokens hoeven niet door spaties te worden begrensd;
- hierdoor zijn keywords in variabelenamen gevaarlijk.

Binnen strings:

```basic
10 print "play sprite bank"
```

worden de woorden `play`, `sprite` en `bank` **niet** getokeniseerd.

Na `rem`:

```basic
10 rem play sprite bank
```

blijft de rest van de regel tekst.

Na `data` blijft de DATA-inhoud letterlijk tot een dubbele punt buiten quotes:

```basic
10 data play,sprite,"bank":read a$,b$,c$
```

Daarna wordt na de `:` weer normaal getokeniseerd.

### 2.6 Testen

Gebruik bij voorkeur VICE:

```bash
x128 programma.prg
```

Op een echte C128 kan een normale BASIC PRG worden geladen en gestart.

Controleer altijd dat de machine in **C128 mode** staat. Een BASIC 7.0 PRG is geen
C64 BASIC V2-programma.

---

## 3. Volledige BASIC 7.0 tokentabel

### 3.1 Basis- en één-byte tokens

| Hex | Keyword | Hex | Keyword | Hex | Keyword |
|---|---|---|---|---|---|
| 80 | `end` | 81 | `for` | 82 | `next` |
| 83 | `data` | 84 | `input#` | 85 | `input` |
| 86 | `dim` | 87 | `read` | 88 | `let` |
| 89 | `goto` | 8A | `run` | 8B | `if` |
| 8C | `restore` | 8D | `gosub` | 8E | `return` |
| 8F | `rem` | 90 | `stop` | 91 | `on` |
| 92 | `wait` | 93 | `load` | 94 | `save` |
| 95 | `verify` | 96 | `def` | 97 | `poke` |
| 98 | `print#` | 99 | `print` | 9A | `cont` |
| 9B | `list` | 9C | `clr` | 9D | `cmd` |
| 9E | `sys` | 9F | `open` | A0 | `close` |
| A1 | `get` | A2 | `new` | A3 | `tab(` |
| A4 | `to` | A5 | `fn` | A6 | `spc(` |
| A7 | `then` | A8 | `not` | A9 | `step` |
| AA | `+` | AB | `-` | AC | `*` |
| AD | `/` | AE | `^` | AF | `and` |
| B0 | `or` | B1 | `>` | B2 | `=` |
| B3 | `<` | B4 | `sgn` | B5 | `int` |
| B6 | `abs` | B7 | `usr` | B8 | `fre` |
| B9 | `pos` | BA | `sqr` | BB | `rnd` |
| BC | `log` | BD | `exp` | BE | `cos` |
| BF | `sin` | C0 | `tan` | C1 | `atn` |
| C2 | `peek` | C3 | `len` | C4 | `str$` |
| C5 | `val` | C6 | `asc` | C7 | `chr$` |
| C8 | `left$` | C9 | `right$` | CA | `mid$` |
| CB | `go` | CC | `rgr` | CD | `rclr` |
| CE | functie-prefix | CF | `joy` | D0 | `rdot` |
| D1 | `dec` | D2 | `hex$` | D3 | `err$` |
| D4 | `instr` | D5 | `else` | D6 | `resume` |
| D7 | `trap` | D8 | `tron` | D9 | `troff` |
| DA | `sound` | DB | `vol` | DC | `auto` |
| DD | `pudef` | DE | `graphic` | DF | `paint` |
| E0 | `char` | E1 | `box` | E2 | `circle` |
| E3 | `gshape` | E4 | `sshape` | E5 | `draw` |
| E6 | `locate` | E7 | `color` | E8 | `scnclr` |
| E9 | `scale` | EA | `help` | EB | `do` |
| EC | `loop` | ED | `exit` | EE | `directory` |
| EF | `dsave` | F0 | `dload` | F1 | `header` |
| F2 | `scratch` | F3 | `collect` | F4 | `copy` |
| F5 | `rename` | F6 | `backup` | F7 | `delete` |
| F8 | `renumber` | F9 | `key` | FA | `monitor` |
| FB | `using` | FC | `until` | FD | `while` |
| FE | statement-prefix | FF | `{pi}` / π |  |  |

### 3.2 `$CE` uitgebreide functies

| Bytes | Functie |
|---|---|
| `CE 02` | `pot` |
| `CE 03` | `bump` |
| `CE 04` | `pen` |
| `CE 05` | `rsppos` |
| `CE 06` | `rsprite` |
| `CE 07` | `rspcolor` |
| `CE 08` | `xor` |
| `CE 09` | `rwindow` |
| `CE 0A` | `pointer` |

### 3.3 `$FE` uitgebreide statements

| Bytes | Statement | Bytes | Statement |
|---|---|---|---|
| `FE 02` | `bank` | `FE 03` | `filter` |
| `FE 04` | `play` | `FE 05` | `tempo` |
| `FE 06` | `movspr` | `FE 07` | `sprite` |
| `FE 08` | `sprcolor` | `FE 09` | `rreg` |
| `FE 0A` | `envelope` | `FE 0B` | `sleep` |
| `FE 0C` | `catalog` | `FE 0D` | `dopen` |
| `FE 0E` | `append` | `FE 0F` | `dclose` |
| `FE 10` | `bsave` | `FE 11` | `bload` |
| `FE 12` | `record` | `FE 13` | `concat` |
| `FE 14` | `dverify` | `FE 15` | `dclear` |
| `FE 16` | `sprsav` | `FE 17` | `collision` |
| `FE 18` | `begin` | `FE 19` | `bend` |
| `FE 1A` | `window` | `FE 1B` | `boot` |
| `FE 1C` | `width` | `FE 1D` | `sprdef` |
| `FE 1E` | `quit` — **niet geïmplementeerd** | `FE 1F` | `stash` |
| `FE 21` | `fetch` | `FE 23` | `swap` |
| `FE 24` | `off` — **niet geïmplementeerd** | `FE 25` | `fast` |
| `FE 26` | `slow` |  |  |

De ongebruikte tweede bytes `$20` en `$22` zijn bewust niet als keyword opgenomen.

---

## 4. Variabelen, typen en expressies

### 4.1 Naamgeving

Veilige stijl:

```basic
10 rem -- variabelen --
20 rem px,py=spelerpositie  sc=score  lv=levens
30 rem j=joystick  k$=toets  i,n=lussen  a$=tekst
```

Gebruik deze stijl consequent.

Vermijd:

```basic
10 score=100
20 total=10
30 duration=60
40 before=1
```

Reden:

- `score` bevat `or`;
- `total` bevat `to`;
- `duration` bevat `on`;
- `before` bevat onder andere `for`/`or`.

### 4.2 Systeemnamen

Niet als eigen opslag gebruiken:

```text
ds
ds$
el
er
err$
st
ti
ti$
```

Deze geven onder andere diskstatus, errorinformatie, I/O-status en systeemklok terug.

### 4.3 Typen

```basic
10 a=3.14159
20 i%=123
30 a$="c128"
```

- normaal numeriek: floating point;
- `%`: signed integer;
- `$`: string;
- integerbereik: `-32768..32767`;
- stringlengte: maximaal 255 bytes.

### 4.4 Operatoren

```text
+  -  *  /  ^
=  <  >  <=  >=  <>
and  or  xor  not
```

Gebruik haakjes wanneer de bedoeling niet triviaal is.

```basic
10 if (j and 128)=128 then print "fire"
```

---

## 5. Control flow

### 5.1 IF / THEN

```basic
10 if a=1 then print "a is 1"
20 if a<>1 then 100
```

### 5.2 ELSE

Bij BASIC 7.0 bestaat `else` wel.

De dubbele punt vóór `else` is verplicht:

```basic
10 if a<10 then print "laag":else print "hoog"
```

Niet schrijven:

```basic
10 if a<10 then print "laag" else print "hoog"
```

### 5.3 BEGIN / BEND

Gebruik dit wanneer een IF-tak meerdere programmaregels omvat.

```basic
10 if a=1 then begin:print "start"
20 print "meer dan een regel"
30 print "nog een regel"
40 bend:else print "a is niet 1"
50 end
```

Met beide takken als blok:

```basic
10 if a=1 then begin:print "true"
20 print "true blok"
30 bend:else begin:print "false"
40 print "false blok"
50 bend
60 end
```

Regels:

- `begin` hoort bij `then` of `else`;
- plaats `:` tussen `begin` en een statement op dezelfde regel;
- `else` na een blok staat op dezelfde regel als de bijbehorende `bend`;
- nest alleen wanneer de structuur duidelijk blijft.

### 5.4 FOR / NEXT

```basic
10 for i=1 to 10
20 print i
30 next i
```

Met stap:

```basic
10 for x=100 to 0 step -5
20 print x
30 next x
```

### 5.5 DO / LOOP

Oneindig:

```basic
10 do
20 print "loop"
30 loop
```

Voorwaarde vóór de body:

```basic
10 do while a<10
20 a=a+1
30 loop
```

```basic
10 do until a=10
20 a=a+1
30 loop
```

Voorwaarde na de body:

```basic
10 do
20 a=a+1
30 loop while a<10
```

```basic
10 do
20 a=a+1
30 loop until a=10
```

Vroegtijdig verlaten:

```basic
10 do
20 getkey k$
30 if k$="q" then exit
40 loop
50 print "klaar"
```

### 5.6 GOSUB / RETURN

```basic
10 gosub 1000
20 end
1000 print "subroutine"
1010 return
```

Elke normale subroutine eindigt via `return`.

### 5.7 ON ... GOTO / GOSUB

```basic
10 on n goto 100,200,300
```

```basic
10 on n gosub 1000,2000,3000
20 print "terug"
```

Elke door `ON ... GOSUB` opgegeven regelnummer moet **exact** bestaan als een
echte programmaregel; de syntax checker rapporteert ontbrekende doelen als
[MISSING_TARGET]. Plaats elke subroutine-body dus precies op het genoemde
regelnummer (geen offset zoals 2210 als de lijst 2200 bevat) — anders faalt
de dispatch direct.

Elke aangeroepen subroutine moet zelfstandig eindigen met `return`:

```basic
2060 on rm gosub 2100,2200,2300,2400,2500,2600
...
2100 print "...":return
2200 print "...":return
```

De eerste tak mag niet alleen een "rem + return" zijn waarna de echte tekst
pas op een vervolg-regel volgt; dan klopt de dispatch niet.

### 5.8 DATA / READ / RESTORE

```basic
10 read a$,n
20 print a$,n
30 data hello,128
```

`data` hoeft niet uitvoerbaar bereikbaar te zijn; `read` gebruikt de DATA-pointer.

### 5.9 TRAP / RESUME

BASIC 7.0 heeft native foutafhandeling.

```basic
10 trap 1000
20 input "getal";a
30 b=100/a
40 print b
50 end
1000 print err$(er);" in line";el
1010 resume next
```

Mogelijke vormen:

```basic
resume
resume next
resume 500
```

Zet trapping uit met:

```basic
trap
```

---

## 6. 40-koloms VIC en 80-koloms VDC

### 6.1 Dit onderscheid is fundamenteel

De C128 heeft twee verschillende videosystemen:

- 40-koloms VIC-II: tekst, bitmapgraphics en sprites;
- 80-koloms VDC: tekstweergave en eigen videogeheugen.

Schrijf nooit code alsof één schermgeheugen beide displays representeert.

### 6.2 GRAPHIC-modi

```text
0 = 40-koloms tekst
1 = standaard bitmap
2 = standaard bitmap + split text
3 = multicolor bitmap
4 = multicolor bitmap + split text
5 = 80-koloms tekst
```

Voorbeelden:

```basic
10 graphic 0
20 scnclr 0
```

```basic
10 graphic 5
20 scnclr 5
```

Bitmap:

```basic
10 graphic 1,1
20 color 0,1
30 color 1,2
40 draw 1,0,0 to 319,199
```

### 6.3 GRAPHIC clear/split

Algemene vorm:

```text
graphic mode[,clear][,split]
```

`clear=1` maakt de gekozen graphicsruimte schoon.

Bij een nieuw bitmapprogramma:

```basic
10 graphic 1,1
```

Gebruik `graphic clr` wanneer de gereserveerde graphicsruimte weer moet worden
vrijgegeven volgens het BASIC 7.0 geheugenmodel.

### 6.4 SCNCLR

Gebruik bij voorkeur native `scnclr` in plaats van C64-achtige `print chr$(147)` hacks.

```basic
10 scnclr 0
```

voor het 40-kolomsscherm.

```basic
10 scnclr 5
```

voor het 80-kolomsscherm.

### 6.5 COLOR

Bronnummers:

```text
0 = 40-col VIC achtergrond
1 = bitmap/VIC voorgrond
2 = multicolor 1
3 = multicolor 2
4 = 40-col VIC rand
5 = tekenkleur op 40- of 80-kolommen
6 = 80-col VDC achtergrond
```

Kleuren zijn `1..16`.

Voorbeeld:

```basic
10 color 0,1
20 color 4,7
30 color 5,2
```

### 6.6 WINDOW

Native tekstvensters werken op 40 of 80 kolommen:

```text
window left,top,right,bottom[,clear]
```

40-col voorbeeld:

```basic
10 graphic 0
20 window 2,2,37,20,1
30 print "binnen het venster"
```

80-col voorbeeld:

```basic
10 graphic 5
20 window 5,2,74,22,1
30 print "80 column window"
```

Kolommen:

- 40-col: `0..39`;
- 80-col: `0..79`;
- rijen: `0..24`.

Met `rwindow(n)` kun je informatie over het actieve window/display opvragen.

### 6.7 CHAR

`char` kan tekst positioneren zonder C64-cursor-POKE-trucs.

Algemene vorm:

```text
char [colorsource],x,y[,string][,reverse]
```

Voorbeeld:

```basic
10 graphic 0
20 char 1,10,5,"hello",0
```

---

## 7. Native bitmapgraphics

Gebruik de BASIC 7.0 grafische opdrachten in plaats van individuele VIC-register-POKEs
wanneer dat functioneel voldoende is.

### 7.1 DRAW

```basic
10 graphic 1,1
20 draw 1,10,10 to 100,60
```

Meerdere segmenten:

```basic
10 draw 1,10,10 to 10,60 to 100,60 to 10,10
```

### 7.2 BOX

```text
box [color],x1,y1[,x2,y2][,angle][,paint]
```

```basic
10 graphic 1,1
20 box 1,10,10,100,60
30 box 1,120,40,200,100,45,1
```

### 7.3 CIRCLE

Gebruik `circle` voor cirkels, ellipsen, bogen en polygonale benaderingen. Begin altijd
met een geldige bitmapmodus.

Eenvoudig:

```basic
10 graphic 1,1
20 circle 1,160,100,50
```

### 7.4 PAINT

Vult een begrensd gebied.

```basic
10 graphic 1,1
20 circle 1,160,100,50
30 paint 1,160,100
```

### 7.5 LOCATE

Verplaatst de grafische pixelcursor:

```basic
10 locate 100,50
20 draw
```

### 7.6 SCALE

Gebruik de native schaalinstelling wanneer relatieve grafische coördinaten gewenst zijn.
Beoordeel altijd de actuele coordinate-mode voordat code wordt gecombineerd.

### 7.7 SSHAPE / GSHAPE

Een bitmapgebied kan naar een string worden opgeslagen:

```text
sshape a$,x1,y1[,x2,y2]
```

en teruggeplaatst:

```text
gshape a$[,x,y][,mode]
```

GSHAPE-mode:

```text
0 = normaal
1 = invert
2 = OR
3 = AND
4 = XOR
```

---

## 8. Sprites — gebruik BASIC 7.0, niet standaard VIC-POKEcode

### 8.1 SPRITE

Algemene vorm:

```text
sprite number[,on][,color][,priority][,xexp][,yexp][,multicolor]
```

Bereiken:

```text
number     1..8
on         0/1
color      1..16
priority   0 voor objecten, 1 achter objecten
xexp       0/1
yexp       0/1
multicolor 0/1
```

Voorbeeld:

```basic
10 sprite 1,1,3
20 movspr 1,100,100
```

Volledig:

```basic
10 sprite 1,1,7,0,1,1,0
20 movspr 1,100,100
```

Niet opgegeven parameters houden bij vervolg-SPRITE-statements de eerdere instelling.

### 8.2 MOVSPR

Absolute positie:

```basic
10 movspr 1,100,80
```

Relatief:

```basic
10 movspr 1,+10,-4
```

Afstand/richting:

```basic
10 movspr 1,50;90
```

Automatische beweging op hoek en snelheid:

```basic
10 movspr 1,45#5
```

- sprite: `1..8`;
- hoek: `0..360`;
- snelheid: `0..15`.

Sprites gebruiken een ander coördinatenstelsel dan de bitmap.

### 8.3 SPRCOLOR

Globale multicolorbronnen voor sprites:

```basic
10 sprcolor 3,7
```

Kleuren `1..16`.

### 8.4 SPRSAV

Spritebeeld ↔ string of sprite ↔ sprite:

```basic
10 sprsav 1,a$
20 sprsav a$,2
30 sprsav 2,3
```

Een sprite bevat 63 databytes; bij string → sprite worden alleen de eerste 63 bytes
gebruikt.

### 8.5 SPRDEF

`sprdef` is een interactieve sprite-editor en is primair geschikt voor handmatig
ontwikkelen, niet als kern van een automatisch gegenereerd runtimeprogramma.

Voor reproduceerbare AI-code:

- lever spritebytes/data deterministisch aan;
- gebruik `sprsav`;
- of laad vooraf opgeslagen spritegegevens met `bload`.

Werkend patroon: sprite-bytes als DATA, inlezen in een numerieke array, omzetten
naar een 63-byte string en laden met `sprsav`:

```basic
170 dim sb(20)
180 for i=0 to 20:read sb(i):next i
210 s$=""
220 for i=0 to 20
230 s$=s$+chr$(0)+chr$(sb(i))+chr$(0)
240 next i
250 sprsav s$,1
```

Dit bouwt een 21-rij sprite waarbij alleen de middelste byte per rij significant
is (de C128-sprite is 24x21 pixels, 3 bytes per rij). Deterministisch en
reproduceerbaar, precies zoals voor AI-code vereist.

### 8.6 Sprite-informatie teruglezen

```basic
10 x=rsppos(1,0)
20 y=rsppos(1,1)
30 s=rsppos(1,2)
```

`rsprite(sprite,characteristic)` leest de eigenschappen terug.

### 8.7 COLLISION en BUMP

Interruptgestuurd:

```basic
10 collision 1,1000
20 collision 2,1100
...
1000 rem sprite-sprite
1010 b=bump(1)
1020 return
1100 rem sprite-display
1110 b=bump(2)
1120 return
```

Zet een collision-handler uit met alleen het type:

```basic
collision 1
```

### 8.8 Bewegende sprite boven tekst zonder graphic-bitmap

Een bobsprite over een 40-koloms **tekst**scherm (`graphic 0`) werkt prima met
`sprite` + `movspr`. Er is geen bitmap-modus nodig zolang je alleen één sprite
wilt animeren terwijl de tekstinhoud zichtbaar blijft. Combineer dit met een
korte `for d=1 to 15:next d` vertraging in de `do`/`loop` voor een redelijke
framerate zonder `sleep`-blokkades op de input.

---

## 9. Joystick, paddles en toetsenbord

### 9.1 GET

Niet-blokkerend:

```basic
10 get k$
20 if k$="" then 10
```

### 9.2 GETKEY

Blokkeert totdat invoer beschikbaar is:

```basic
10 getkey k$
20 print k$
```

Dit is BASIC 7.0-functionaliteit; gebruik het voor menu's en pauzes wanneer wachten
op één toets gewenst is.

### 9.3 JOY

```basic
10 j=joy(2)
```

Poort:

```text
1 = joystickpoort 1
2 = joystickpoort 2
```

Richtingswaarden:

```text
0 = neutraal
1 = boven
2 = rechtsboven
3 = rechts
4 = rechtsonder
5 = onder
6 = linksonder
7 = links
8 = linksboven
```

Fire zet bit 7:

```basic
10 j=joy(2)
20 if (j and 128)=128 then print "fire"
30 d=j and 15
```

### 9.4 POT

Paddles:

```basic
10 p=pot(1)
```

Paddle `1..4`. De waarde bevat de paddlepositie; waarden vanaf 256 signaleren ook
de firebutton.

---

## 10. Geluid en muziek — native BASIC 7.0

De C128 gebruikt nog steeds de SID, maar BASIC 7.0 heeft ingebouwde commando's.
Gebruik die standaard vóór directe SID-register-POKEs.

### 10.1 VOL

```basic
10 vol 8
```

Bereik `0..15`.

### 10.2 SOUND

Algemene vorm:

```text
sound voice,freq,duration[,direction][,minimum][,step][,waveform][,pulsewidth]
```

Belangrijkste bereiken:

```text
voice       1..3
freq        0..65535
duration    0..32767
direction   0=up, 1=down, 2=oscillate
waveform    0=triangle, 1=saw, 2=pulse, 3=noise
pulsewidth  0..4095
```

Eenvoudig:

```basic
10 vol 8
20 sound 1,40960,60
```

### 10.3 ENVELOPE

```text
envelope n[,attack][,decay][,sustain][,release][,waveform][,pulsewidth]
```

Envelope `0..9`; ADSR-waarden `0..15`.

Voorbeeld:

```basic
10 envelope 1,10,5,10,0,2,2048
```

### 10.4 TEMPO

```basic
10 tempo 10
```

Bereik `0..255`.

### 10.5 PLAY

PLAY bevat een muziekstring:

```basic
10 vol 8
20 tempo 10
30 play "v1o4t0u5x0cdefgab"
```

Belangrijke PLAY-elementen:

```text
Vn = voice 1..3
On = octave 0..6
Tn = envelope 0..9
Un = volume 0..9 binnen PLAY
Xn = filter 0/1
A..G = noten
# = kruis
$ = mol
W = hele noot
H = halve
Q = kwart
I = achtste
S = zestiende
. = gepunte noot
R = rust
M = wacht tot stemmen maat afronden
```

### 10.6 FILTER

```text
filter [freq][,lowpass][,bandpass][,highpass][,resonance]
```

```basic
10 filter 1024,1,0,0,5
20 play "v1o4t0u7x1cdefg"
```

SID heeft één filter; de instelling beïnvloedt de gefilterde stemmen gezamenlijk.

---

## 11. Disk I/O

Voor een C128 met diskdrive zijn de `D...`-commando's meestal duidelijker dan
C64-stijl `OPEN 15,...`-constructies.

### 11.1 DIRECTORY / CATALOG

```basic
directory
```

of:

```basic
catalog
```

Gebruik in interactieve ontwikkeling de ingebouwde directoryfunctie.

### 11.2 DLOAD / DSAVE / DVERIFY

```basic
dload "demo"
dsave "demo"
dverify "demo"
```

Optioneel kunnen drive/deviceparameters worden gebruikt.

### 11.3 DOPEN / DCLOSE

```basic
10 dopen #1,"score,s",w
20 print#1,"1000"
30 dclose #1
```

Controleer voor productiecode altijd `ds` / `ds$` waar diskfouten relevant zijn.

### 11.4 BLOAD / BSAVE

Voor binaire assets zoals sprites/charsets:

```basic
10 bload "sprites",b0,p3584
```

Opslaan:

```basic
bsave "sprites",b0,p3584 to p4096
```

Let op de geselecteerde bank en exacte adresrange.

### 11.5 HEADER / SCRATCH / RENAME / COPY / COLLECT

Dit zijn echte BASIC 7.0 diskcommando's, maar destructieve diskoperaties moeten nooit
zonder expliciete bedoeling worden gegenereerd.

Vooral `header` en `scratch` kunnen data vernietigen.

---

## 12. BANK en geheugen

### 12.1 Waarom BANK bestaat

C128 heeft meerdere geheugenconfiguraties. `peek`, `poke`, `sys` en `wait` werken
tegen de geselecteerde BASIC-bankconfiguratie.

```basic
10 bank 15
20 a=peek(53280)
```

BASIC 7.0 kent banknummers `0..15`.

De normale standaard is bank 15.

### 12.2 Belangrijke programmageheugenstructuur

Standaard:

```text
BASIC program text : bank 0, start $1C01
BASIC variables    : bank 1, vanaf $0400
max standaardgebied: richting $FF00
```

Een tokenized BASIC-regel bestaat uit:

```text
2 bytes  pointer naar volgende regel
2 bytes  regelnummer (little endian)
n bytes  tokenized BASIC
1 byte   $00 einde regel
```

Na de laatste regel volgt:

```text
00 00
```

### 12.3 Gebruik POKE alleen wanneer native BASIC 7.0 niet genoeg is

Voorkeursvolgorde:

1. native BASIC 7.0 statement/function;
2. gedocumenteerde KERNAL/BASIC-interface;
3. pas daarna `peek`/`poke`/`sys`.

Voorbeeld: gebruik `sprite`, `movspr`, `color`, `sound`, `window` en `graphic`
liever dan dezelfde functie zelf via hardware-registers te reconstrueren.

---

## 13. FAST en SLOW

```basic
10 fast
...
90 slow
```

`fast` zet de 8502 op ongeveer 2 MHz, maar de VIC 40-koloms display wordt daarbij
uitgeschakeld.

Daarom:

- 80-koloms tekstcode kan goed profiteren van `fast`;
- berekeningen zonder zichtbare VIC-output kunnen profiteren;
- vóór zichtbare 40-koloms output terug naar `slow`;
- grafische VIC-data kan onder `fast` worden opgebouwd, maar wordt pas zichtbaar na
  `slow`;
- gebruik `fetch`, `stash`, `swap` voor REU/DMA alleen volgens de daarvoor geldende
  snelheidsvoorwaarden.

Patroon:

```basic
10 fast
20 rem zware berekening
30 for i=1 to 1000:a=a+i:next i
40 slow
50 print a
```

---

## 14. Performance-richtlijnen

BASIC 7.0 is krachtiger dan BASIC V2 maar blijft geïnterpreteerd.

Gebruik deze volgorde:

1. native graphics/sprite/soundcommando's;
2. korte variabelen;
3. veelgebruikte constanten vooraf berekenen;
4. inner loops compact houden;
5. overbodige stringconcatenatie vermijden;
6. `fast` gebruiken wanneer displayvereisten dat toelaten;
7. machinecode alleen voor aantoonbare hotspots.

Niet automatisch C64-optimalisaties kopiëren die BASIC 7.0-native functies vervangen
door veel POKEs. Dat maakt C128-code vaak moeilijker en minder betrouwbaar.

---

## 15. Veelvoorkomende fouten

### `?SYNTAX ERROR`

Controleer in deze volgorde:

1. keyword uit ander BASIC-dialect;
2. keyword in variabelenaam;
3. vergeten `then`;
4. `else` zonder voorafgaande `:`;
5. ontbrekende komma;
6. ontbrekend haakje;
7. verkeerde functie-argumenten;
8. `off` of `quit`;
9. converter zonder `-i`;
10. verkeerde C64-versie van `bas2prg.py`.

### `?LOOP NOT FOUND` / `?LOOP WITHOUT DO`

Controleer `do`/`loop`-paring en nesting.

### `?BEND NOT FOUND`

Controleer `begin`/`bend`-paring en de IF-structuur.

### `?NO GRAPHICS AREA ERROR`

Voer eerst een bitmap-`graphic`-modus uit voordat `draw`, `box`, `circle`, `paint`
of vergelijkbare bitmapbewerkingen worden gebruikt.

### Onzichtbaar 40-kolomsscherm

Controleer of het programma nog in `fast` staat. Gebruik `slow`.

### BASIC 7-opdracht geeft syntax error op C128

Controleer eerst of de computer per ongeluk in **C64 mode** draait.

### PRG laadt maar is onbruikbaar

Controleer:

```text
loadadres moet $1C01 zijn
extended tokenbytes moeten $CE/$FE gebruiken
bron moet met de juiste case-inversie zijn geconverteerd
```

---

## 16. Verificatiechecklist

Voer dit vóór iedere oplevering uit.

- [ ] Doel is expliciet C128 mode / BASIC 7.0.
- [ ] 40- of 80-koloms doel is bekend.
- [ ] Alle regels hebben nummers `0..63999`.
- [ ] Regelnummers zijn strikt oplopend.
- [ ] Geen regel is langer dan 160 tekens.
- [ ] Variabelen zijn bij voorkeur 1-2 tekens.
- [ ] Geen variabele bevat een BASIC-keyword.
- [ ] Geen eigen gebruik van `ds`, `ds$`, `el`, `er`, `err$`, `st`, `ti`, `ti$`.
- [ ] Geen `?` of editorafkortingen in bron.
- [ ] Geen `off` of `quit`.
- [ ] Quotes en haakjes kloppen.
- [ ] Iedere `if` heeft `then`.
- [ ] Iedere `else` heeft de juiste `:`-structuur.
- [ ] Iedere `begin` heeft `bend`.
- [ ] Iedere `for` heeft `next`.
- [ ] Iedere `do` heeft `loop`.
- [ ] `exit` staat in een DO/LOOP.
- [ ] Alle statische sprongdoelen bestaan.
- [ ] Bitmapcommando's worden voorafgegaan door juiste `graphic`-mode.
- [ ] Sprite nummers zijn `1..8`.
- [ ] Kleurwaarden zijn `1..16`.
- [ ] `bank` is `0..15`.
- [ ] `vol` is `0..15`.
- [ ] JOY-poort is 1 of 2.
- [ ] POKE-adres/waarde en actieve BANK zijn bewust gekozen.
- [ ] `c128_syntax_checker.py` geeft 0 ERRORs.
- [ ] `bas2prg.py ... -i` compileert.
- [ ] PRG begint met `01 1c`.
- [ ] Programma is getest in VICE x128 of op echte C128.
- [ ] FAST/SLOW en 40/80-koloms gedrag zijn runtime gecontroleerd.

---

## 17. Templates

### 17.1 Basisskelet 40 kolommen

```basic
10 rem -- c128 basic 7 --
20 graphic 0
30 scnclr 0
40 color 0,1:color 4,1:color 5,2
50 print "commodore 128"
60 getkey k$
70 if k$<>"q" then 60
80 end
```

### 17.2 Basisskelet 80 kolommen

```basic
10 rem -- 80 column --
20 graphic 5
30 scnclr 5
40 color 6,1:color 5,2
50 window 2,1,77,23,1
60 print "commodore 128 - 80 columns"
70 getkey k$
80 end
```

### 17.3 Menu met GETKEY en ELSE

```basic
10 graphic 0:scnclr 0
20 print "1. start"
30 print "2. info"
40 print "q. quit"
50 getkey k$
60 if k$="1" then gosub 1000:goto 10
70 if k$="2" then gosub 2000:goto 10
80 if k$="q" then end:else goto 50
1000 print "start":getkey k$:return
2000 print "info":getkey k$:return
```

### 17.4 DO/LOOP invoer

```basic
10 print "druk q om te stoppen"
20 do
30 getkey k$
40 if k$="q" then exit
50 print k$;
60 loop
70 print:print "klaar"
80 end
```

### 17.5 Joystick game-loop

```basic
10 graphic 0:scnclr 0
20 s$=""
30 for i=1 to 63:s$=s$+chr$(255):next i
40 sprsav s$,1
50 x=120:y=100
60 sprite 1,1,3,0,0,0,0
70 movspr 1,x,y
80 do
90 j=joy(2):d=j and 15
100 if d=1 then y=y-2
110 if d=3 then x=x+2
120 if d=5 then y=y+2
130 if d=7 then x=x-2
140 movspr 1,x,y
150 if (j and 128)=128 then exit
160 loop
170 sprite 1,0
180 end
```

Dit template gebruikt alleen de vier hoofdrichtingen. Voeg diagonalen expliciet toe wanneer
het spel dat nodig heeft.

### 17.6 Bitmapdemo

```basic
10 graphic 1,1
20 color 0,1:color 1,2
30 draw 1,10,10 to 309,10 to 309,189 to 10,189 to 10,10
40 circle 1,160,100,60
50 box 1,130,70,190,130,45,0
60 getkey k$
70 graphic 0
80 end
```

### 17.7 SOUND

```basic
10 vol 8
20 sound 1,40960,60
30 sleep 2
40 vol 0
50 end
```

### 17.8 PLAY

```basic
10 vol 8
20 tempo 10
30 play "v1o4t0u5x0cdefgab"
40 end
```

### 17.9 TRAP

```basic
10 trap 1000
20 input "deler";a
30 print 100/a
40 end
1000 print err$(er);" line";el
1010 resume next
```

---

## 18. Bronhiërarchie voor toekomstige AI-wijzigingen

Gebruik bij twijfel deze prioriteit:

1. **Commodore 128 System Guide**, BASIC 7.0 Encyclopaedia en C128-mode hoofdstukken.
2. **Commodore 128 Programmer's Reference Guide**.
3. **C-128 BASIC 7.0 Internals** voor tokenizer, geheugenopbouw en interpreterdetails.
4. **C64-Wiki BASIC 7.0** voor praktische keywordreferentie en aanvullende voorbeelden.
5. Bekende werkende C128 BASIC 7.0-programma's als runtime-patroon.
6. Pas daarna algemene kennis.

Als twee bronnen botsen:

- vertrouw voor taal-syntax eerst de officiële Commodore-documentatie;
- vertrouw voor interne tokenbytes/geheugenstructuur de ROM/internals-documentatie;
- neem een OCR-fout nooit automatisch over;
- verifieer twijfelgevallen in VICE of op echte hardware.

Belangrijke referentie-URL's:

```text
https://www.c64-wiki.com/wiki/Category:BASIC_7.0
https://www.commodore.ca/manuals/128_system_guide/sect-04.htm
https://www.commodore.ca/manuals/128_system_guide/sect-05.htm
https://www.commodore.ca/manuals/128_system_guide/sect-16.htm
https://www.commodore.ca/manuals/128_system_guide/sect-17a.htm
https://www.commodore.ca/manuals/128_system_guide/sect-18.htm
https://www.commodore.ca/manuals/128_system_guide/sect-20.htm
```

Lokale kennisbronnen:

```text
Commodore_128_Programmers_Reference_Guide.md
C-128 BASIC 7.0 Internals.md
c128basic.d64
```

---

## Appendix A — belangrijkste C128/BASIC 7.0 verschillen met C64/V2

| Onderwerp | C64 BASIC V2 | C128 BASIC 7.0 |
|---|---|---|
| standaard BASIC start | `$0801` | `$1C01` |
| programmageheugen | één 64K context | tekst bank 0, variabelen bank 1 |
| programmaregel | 80 tekens | 160 tekens |
| ELSE | nee | ja |
| DO/LOOP | nee | ja |
| WHILE/UNTIL | nee | ja, bij DO/LOOP |
| BEGIN/BEND | nee | ja |
| error trapping | handmatig | `trap` / `resume` |
| bitmapgraphics | vooral POKE | native `graphic/draw/box/circle/paint` |
| sprites | VIC-registers | native `sprite/movspr/sprsav/...` |
| joystick | CIA PEEK | `joy()` |
| geluid | SID POKE | `sound/play/envelope/filter/tempo/vol` |
| tekstwindow | handmatig | `window` / `rwindow()` |
| bankselectie | C64 memory config hacks | native `bank` |
| disk | OPEN/command channel | extra `dload/dsave/dopen/...` |
| CPU-speed | ongeveer 1 MHz | `fast` / `slow` |
| tokens | hoofdzakelijk 1 byte | 1 byte + `$CE`/`$FE` extended |

---

## Appendix B — snelle foutcorrectie

| Fout patroon | Correct BASIC 7.0 |
|---|---|
| `cls` | `scnclr 0` of `scnclr 5` |
| C64 sprite-POKEs voor normale spritecontrole | `sprite` + `movspr` |
| CIA-PEEK voor normale joystickinput | `joy(1)` / `joy(2)` |
| SID-register-POKEs voor standaard geluid | `sound`, `play`, `envelope`, `filter`, `vol` |
| `while ... wend` | `do while ... : ... : loop` |
| `repeat ... until` | `do : ... : loop until ...` |
| `if ... then ... else ...` zonder `:` | `if ... then ... :else ...` |
| meerdere IF-regels zonder structuur | `then begin ... bend` |
| C64 PRG-loadadres `$0801` | C128 `$1C01` |
| één-byte token voor PLAY | `FE 04` |
| één-byte token voor POT | `CE 02` |
| `quit` / `off` | niet gebruiken; BASIC 7.0 implementeert ze niet |
| 80-col als VIC bitmap behandelen | VDC-tekstmodus expliciet ontwerpen |
| `fast` + zichtbare VIC-output verwachten | `slow` vóór zichtbare 40-col output |

---

## Appendix C — Werkomgeving en tooling-lessen

Deze lessen zijn geen BASIC 7.0-syntax, maar beïnvloeden wel het ontwikkel-
en controleproces in deze workspace.

### C.1 Python-interpreter kan ontbreken op PATH

`python`, `python3` en `py` faalden op dit systeem. Werkende interpreter
(geïnstalleerd door `uv`):

```text
C:\Users\aegwh\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe
```

Les: als `python` niet herkend wordt, zoek dan met
`where /R C:\Users\aegwh python.exe` naar een bruikbare interpreter en gebruik
het volledige quoted pad voor `c128_syntax_checker.py` en `bas2prg.py`.

### C.2 Terminal is cmd.exe, niet PowerShell

Ondanks dat de systeeminfo `WindowsPowerShell\v1.0\powershell.exe` als default
shell noemt, voerde de terminal commando's uit als **cmd.exe**: `Select-Object`
werd niet herkend en `&` chaining werkte wel (`&` is cmd, niet PowerShell waar
`;` geldt). Les: gebruik in deze workspace cmd-syntax (`&`, `2>nul`, `where /R`)
en vermijd PowerShell-cmdlets tenzij expliciet in een PowerShell-terminal.

### C.3 read_file slice met offset voorbij bestand geeft "File is empty"

`read_file` met `mode: slice` en een offset groter dan de bestandslengte
retourneert "Note: File is empty" in plaats van een foutmelding. Dit is
misleidend: het bestand was niet leeg, alleen lag de offset buiten bereik.
Les: vertrouw niet op die "empty"-melding bij een hoge offset; controleer de
bestandsgrootte of gebruik een lagere offset/`limit`.

### C.4 apply_diff kan niet om `=======` in zoekinhoud

Het `apply_diff`-formaat scheidt SEARCH/REPLACE met een regel die exact
`=======` bevat. Bevat de te zoeken broncode zelf een regel met louter
`=======` (bijv. een ASCII-scheiding in een comment of markdown-codeblok),
dan breekt de parser met `marker '=======' found in your diff content`.
De backslash-escape werkt alleen voor inhoud die exact die marker is.

Les: vermijd `apply_diff` wanneer de zoekinhoud een `=======`-regel kan
bevatten. Gebruik dan `write_to_file` voor de hele file, of bewerk het
bestand rechtstreeks via Python (`open(...,newline='')` om regeleinden te
bewaren) of PowerShell (`Get-Content -Raw` +
`[System.IO.File]::WriteAllText` met `UTF8Encoding($false)`).

### C.5 Regeleinden controleren vóór een multi-line vervanging

Controleer of een bestand LF of CRLF gebruikt voordat je een multi-line
zoekstring bouwt, anders werkt `.Contains()` niet:

```powershell
$bytes = [System.IO.File]::ReadAllBytes('bestand.md')
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
$idx = $text.IndexOf('anker tekst')
if ($idx -ge 0) { Write-Output ([int]$text[$idx-1]) }  # 10 = LF, 13 = CR
```

Bij LF gebruik je `` `n `` in PowerShell (of `\n` in Python); bij CRLF gebruik
je `` `r`n `` (of `\r\n`).
