# C128 BASIC 7.0 Syntax Checker

Dit document beschrijft de statische checker `c128_syntax_checker.py` die bij
`c128_basic_skill.md` hoort.

## Doel

De checker vangt fouten op die AI-gegenereerde Commodore 128 BASIC 7.0 code vaak
onbruikbaar maken voordat de bron naar een PRG wordt geconverteerd.

Doelplatform:

```text
Commodore 128 native mode
Commodore BASIC 7.0
tekstbron .bas
```

De checker is geen emulator. Een resultaat met 0 ERRORs betekent dat alle
geïmplementeerde statische controles slagen; runtime-testen in VICE x128 of op echte
hardware blijft verplicht.

## Gebruik

```bash
python c128_syntax_checker.py programma.bas
```

Machineleesbaar:

```bash
python c128_syntax_checker.py programma.bas --json
```

Bereikbaarheidswaarschuwingen uit:

```bash
python c128_syntax_checker.py programma.bas --no-reach
```

of:

```bash
C128_NO_REACH=1 python c128_syntax_checker.py programma.bas
```

Exitcodes:

```text
0 = geen ERRORs
1 = minstens één ERROR
2 = invoerbestand kon niet worden gelezen / CLI-fout
```

## Controles

### Regelnummers

- verplicht;
- `0..63999`;
- uniek;
- strikt oplopend.

### Regellengte

Een bronregel mag maximaal 160 tekens bevatten.

### Quotes en haakjes

De checker meldt:

- oneven aantal dubbele quotes;
- sluitend haakje zonder opener;
- niet-gesloten haakjes.

### Statementherkenning

Bekende BASIC 7.0 statements zijn toegestaan.

Voorbeelden die worden afgekeurd:

```basic
10 cls
20 while a<10
30 wend
```

`while` is in BASIC 7.0 alleen een modifier van `do` of `loop`, niet een
`WHILE/WEND`-constructie uit een ander dialect.

Gebruik:

```basic
10 do while a<10
20 a=a+1
30 loop
```

### Niet-geïmplementeerde tokens

De ROM kent tokens voor:

```text
off
quit
```

maar BASIC 7.0 implementeert de opdrachten niet. De checker geeft daarom een ERROR.

### Variabelen

De checker waarschuwt bij namen langer dan twee tekens en meldt een ERROR wanneer:

- een variabele een BASIC-keyword bevat;
- verschillende namen op dezelfde eerste twee significante tekens botsen;
- een gereserveerde systeemnaam als gewone schrijfvariabele wordt gebruikt.

Systeemnamen:

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

Veilige AI-stijl:

```basic
10 sc=100
20 px=120:py=80
30 k$=""
```

### IF / THEN / ELSE

Afgevangen:

- `if` zonder `then`;
- `else` zonder voorafgaande dubbele punt;
- `else` zonder logische IF/BEND-context.

Goed:

```basic
10 if a=1 then print "ja":else print "nee"
```

### BEGIN / BEND

De checker houdt een blokstack bij.

Afgevangen:

- `begin` zonder passende IF/ELSE-context;
- `bend` zonder `begin`;
- `begin` zonder latere `bend`.

### FOR / NEXT

Afgevangen:

- `next` zonder `for`;
- niet-passende lusvariabele;
- `for` zonder `next`.

### DO / LOOP / EXIT

Afgevangen:

- `loop` zonder `do`;
- `do` zonder `loop`;
- `exit` buiten een actieve DO/LOOP.

### Sprongdoelen

Voor statisch numerieke doelen controleert de checker:

```text
goto
go to
gosub
then <line>
else <line>
trap <line>
resume <line>
restore <line>
on ... goto
on ... gosub
collision type,<line>
```

Een ontbrekende doelregel is een ERROR.

### Functie-argumenten

Voor een relevante subset ingebouwde functies wordt het aantal argumenten gecontroleerd,
onder andere:

```text
abs asc atn chr$ cos dec err$ exp fre hex$
instr int joy left$ len log mid$ peek pen pointer
pos pot bump rdot right$ rnd rsppos rsprite rwindow
sgn sin sqr str$ tan val
```

### Statische bereiken

Wanneer parameters letterlijke gehele getallen zijn:

```text
bank          0..15
graphic       0..5
vol           0..15
tempo         0..255
sprite        1..8
movspr sprite 1..8
sound voice   1..3
pot           1..4
color source  0..6
color value   1..16
poke address  0..65535
poke value    0..255
window x      0..79
window y      0..24
```

Een expressie of variabele als parameter wordt niet numeriek geëvalueerd.

### Interactieve opdrachten

De checker geeft een WARNING bij enkele opdrachten die vooral bij interactief
programmeren/editing horen, bijvoorbeeld `auto`, `renumber`, `monitor` en `sprdef`.

Dit is bewust een WARNING: controleer het beoogde gebruik in plaats van automatisch
code te herschrijven.

### Bereikbaarheid

Er is een lichte control-flow-analyse die regels kan markeren als `UNREACHABLE`.

Dit is indicatief. BASIC heeft dynamische en speciale control-flowpatronen die een
statische checker niet volledig kan bewijzen.

DATA-regels worden niet als onbereikbaar gemeld alleen omdat uitvoering er niet langs
loopt.

Schakel deze analyse uit wanneer hij bij een correct programma ruis veroorzaakt:

```bash
python c128_syntax_checker.py programma.bas --no-reach
```

## Wat de checker bewust niet beweert

De checker:

- emuleert BASIC 7.0 niet;
- voert expressies niet uit;
- controleert geen spritebeelddata;
- weet bij dynamische waarden niet welke kleur/bank/coördinaat uiteindelijk ontstaat;
- bewijst geen diskbestand of device;
- bewijst geen timing;
- bewijst geen correcte VDC/VIC hardware-interactie;
- kan machinecode achter `sys` niet valideren.

Daarom blijft de workflow:

```text
.bas
  |
  v
c128_syntax_checker.py
  |
  | 0 ERRORs
  v
bas2prg.py -i
  |
  v
.prg
  |
  v
VICE x128 / echte C128
```

## Integratie met een AI-agent

Geef de agent deze instructie:

1. Lees `c128_basic_skill.md`.
2. Schrijf uitsluitend C128 BASIC 7.0.
3. Sla bron op als `.bas` in kleine letters.
4. Draai de checker.
5. Corrigeer iedere ERROR.
6. Compileer met de C128 `bas2prg.py` en `-i`.
7. Inspecteer bij tokenizerproblemen `--dump`.
8. Test de PRG in C128-mode.
9. Lever geen code op die alleen theoretisch plausibel is.

## Voorbeeld — geldige bron

```basic
10 graphic 0
20 scnclr 0
30 print "druk q"
40 do
50 getkey k$
60 if k$="q" then exit
70 print k$;
80 loop
90 end
```

## Voorbeeld — fouten die moeten worden gevonden

```basic
10 cls
20 score=1
30 bank 17
40 sprite 9,1,3
50 if a=1 print "then ontbreekt"
60 do
70 print "geen loop"
80 goto 999
```

Verwachte categorieën:

```text
UNKNOWN_STATEMENT
KEYWORD_IN_VARIABLE
RANGE
IF_THEN
DO_WITHOUT_LOOP
MISSING_TARGET
```

## Relatie met bas2prg.py

De checker valideert de tekstbron. `bas2prg.py` doet daarna de echte tokenisatie.

Belangrijk:

```text
C128 BASIC start = $1C01
PLAY              = FE 04
SPRITE            = FE 07
POT               = CE 02
```

Gebruik nooit de C64 BASIC V2-converter voor BASIC 7.0 bron.
