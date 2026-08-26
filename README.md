# 🕹️ C128 BASIC AI Skillset

Een complete toolkit en skillset om met AI-assistentie betrouwbare **Commodore 128 BASIC 7.0** programma's te schrijven, controleren en compileren — van platte `.bas` tekstbron tot een draaiende `PRG` op echte hardware of in VICE `x128`.

```
   ┌──────────┐    check     ┌──────────┐   convert    ┌──────────┐    run     ┌──────────┐
   │  AI /    │ ───────────▶ │ syntax   │ ───────────▶ │ bas2prg  │ ─────────▶ │  PRG     │
   │  jij     │              │ checker  │              │  (-i)    │            │  $1C01   │
   └──────────┘              └──────────┘              └──────────┘            └──────────┘
        │                        │                          │                       │
        └── .bas (kleine letters, verplichte regelnummers) └─▶ VICE x128 / echte C128
```

## 🎯 Doel

AI-gegenereerde BASIC-code faalt vaak subtiel: verkeerde commando's (BASIC V2- of QuickBASIC-denken), ontbrekende regelnummers, case-problemen bij tokenizing, of een verkeerd load-adres. Deze repo pakt dat aan met drie onderdelen:

| Onderdeel | Bestand | Wat het doet |
|---|---|---|
| 📘 **Skill** | [`c128_basic_skill.md`](c128_basic_skill.md) | Complete werkinstructie voor de AI: syntax, control flow, graphics, sprites, SID, BANK-geheugen, joystick, disk I/O en de verplichte 12-staps werkvolgorde. |
| 🔍 **Checker** | [`c128_syntax_checker.py`](c128_syntax_checker.py) + [docs](c128_syntax_checker.md) | Statische checker die fouten vangt *voordat* er gecompileerd wordt (regelnummers, keywords, GOTO/THEN/GOSUB-doelen, bereikbaarheid, 2-teken variabele-uniekheid, ...). |
| 🛠️ **Converter** | [`bas2prg.py`](bas2prg.py) | `.bas` → `PRG` tokenizer met C128-ondersteuning en `invert_case=True` / `-i`; output begint op load-adres `$1C01`. |

Plus een demoprogramma: [`pong.bas`](pong.bas) → [`pong.prg`](pong.prg), en een toolchain-test in [`test_c128_toolchain.py`](test_c128_toolchain.py).

## 🚀 Quickstart

```bash
# 1. Check je bron
python c128_syntax_checker.py pong.bas

# 2. Converteer (case-inversie is verplicht voor C128 PRG's)
python bas2prg.py -i pong.bas

# 3. Test in VICE (C128 mode)
x128 pong.prg
```

Machineleesbare output voor AI-loops:

```bash
python c128_syntax_checker.py pong.bas --json
```

Exitcodes van de checker: `0` = schoon, `1` = minstens één ERROR, `2` = CLI/leesfout.

## 📋 De verplichte werkvolgorde (TL;DR)

1. Bepaal 40-koloms (VIC), 80-koloms (VDC) of beide.
2. Alleen BASIC 7.0-constructies uit de skill gebruiken.
3. Platte `.bas`, kleine letters, regelnummers in stappen van 10.
4. Variabelen uniek op de eerste twee significante tekens.
5. Checker draaien → **0 ERRORs** is de minimumeis.
6. Converteren met `-i` (`invert_case`).
7. Controleren dat de PRG met `$1C01` begint.
8. Testen in VICE `x128` en op echte hardware.
9. Nieuwe inzichten wegschrijven naar `newskills.md`.

## 📁 Repo-indeling

```
.
├── c128_basic_skill.md              # De skill: volledige BASIC 7.0 werkinstructie
├── c128_syntax_checker.md           # Documentatie van de checker
├── c128_syntax_checker.py           # De checker zelf
├── bas2prg.py                       # .bas → PRG tokenizer/converter
├── pong.bas / pong.prg              # Demo: Pong in BASIC 7.0
├── test_c128_toolchain.py           # End-to-end toolchain tests
└── .roo/skills/commodore128basicdeveloper/SKILL.md  # Skill als Roo/AI-mode
```

## ⚠️ Randvoorwaarden

- Doelplatform: **Commodore 128 / 128D / 128DCR**, native C128 mode, **BASIC 7.0**, RAM bank 0 vanaf `$1C01`.
- De checker is geen emulator: 0 ERRORs betekent niet automatisch dat het programma correct draait — runtime-testen blijft verplicht.
- Geen BASIC V2-aannames, geen QuickBASIC/GW-BASIC/VB-commando's tenzij expliciet gedocumenteerd.

## 🤖 Waarom voor AI?

De skill is geschreven als system-prompt-achtige werkinstructie: hij dwingt de AI in het juiste dialect te denken, en de checker fungeert als harde poortwachter in de compile-loop. Resultaat: minder hallucinerende keywords, minder stille tokenizing-fouten, en code die de eerste keer daadwerkelijk `READY.` teruggeeft.

---

*Binnen korte tijd toont jouw C128 trots `**** COMMODORE 128 BASIC V7.0 122365 BYTES FREE ****` met jouw eigen PRG erop.* 💾
