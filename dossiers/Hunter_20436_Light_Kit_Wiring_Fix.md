# 💡 REPAIR GUIDE: HUNTER 20436 BIG LEAGUE LIGHT KIT WIRING FIX
**Model:** Hunter 20436 Big League (44-Inch Baseball Theme Ceiling Fan)  
**Symptom:** Motor works 100%, but light kit does NOT turn on due to miswiring inside the switch housing.  
**Auditor:** Victory Hale (HALE-AG, 4-Star Lead Orchestrator)  
**Date:** July 27, 2026  

---

## ⚠️ SAFETY FIRST: PRE-REPAIR CHECKLIST
1. **Turn OFF Power:** Flip the circuit breaker for the fan off at your main breaker panel.
2. **Verify Zero Power:** Use a non-contact tester on the fan switch housing to confirm electricity is completely off before opening.

---

## 🔍 1. WHY THE LIGHT FAILS WHILE MOTOR WORKS
On the Hunter 20436, the fan motor and light kit receive power through **two separate hot feed wires** coming down from the ceiling through the fan downrod into the lower switch housing:
* **Black Wire:** Power feed for the **Fan Motor**.
* **Blue Wire (or Black with White Stripe):** Power feed for the **Light Kit**.
* **White Wire:** Shared **Neutral Ground** for both motor and light.

If the motor works but the light does not, the light's power circuit is broken at one of 3 miswired points inside the lower switch housing.

---

## 🔧 2. STEP-BY-STEP REPAIR & CORRECT WIRING DIAGRAM

```
================================================================================
          HUNTER 20436 LOWER SWITCH HOUSING CORRECT WIRING SCHEMATIC            
================================================================================

 CEILING / DOWNROD HARNESS (From Top)          LIGHT KIT & SWITCH HOUSING
 ----------------------------------          ----------------------------
 
  [ BLUE (Light Hot Feed) ] ───────────────► [ Light Pull Chain Switch (Port L) ]
                                              [ Light Pull Chain Switch (Port 1) ]
                                                    │
                                                    ▼ (Black wire to light socket)
                                              [ LIGHT BULB CENTER TERMINAL ]

  [ WHITE (Shared Neutral) ] ──────────────► [ LIGHT BULB SCREW SHELL (White Wire) ]
                                              AND [ Motor Capacitor White Wire ]

  [ BLACK (Motor Hot Feed) ] ──────────────► [ Motor 3-Speed Switch (Port L) ]
================================================================================
```

---

## 🛠️ 3. THE 3 COMMON MISWIRING MISTAKES & HOW TO FIX THEM

### MISTAKE #1: The Blue Wire is Not Connected to the Light Switch
* **Problem:** The Blue wire coming from the downrod harness was left disconnected or capped with a wire nut inside the upper canopy or switch housing.
* **Fix:** Connect the **Blue wire** coming from the downrod harness directly to the **Input (L) terminal** of the Light Pull-Chain Switch (or the Black wire of the light kit).

### MISTAKE #2: The Light Kit White Neutral Wire is Unhooked
* **Problem:** The light socket’s **White wire** was not tied into the main **White Neutral wire bundle**.
* **Fix:** Join the White wire from the light socket together with the main White Neutral wire coming from the ceiling/downrod harness using a twist-on wire nut.

### MISTAKE #3: Blown Wattage Limiter (Hunter Safety Feature)
* **Problem:** 2000s-era Hunter fans include a small black or white 190W **wattage limiter module** in the switch housing. If a bulb over 100W was used, the internal limiter fuse pops permanently, killing the light circuit even if wired correctly.
* **Fix:** Bypass the wattage limiter by connecting the Blue wire directly to the light switch, bypassing the limiter box.

---

## 📋 4. REPAIR VERIFICATION STEPS
1. Remove 3 housing screws to open the lower switch cap under the motor.
2. Confirm **Blue (Hot)** is attached to the light switch input.
3. Confirm **White (Neutral)** is tied into the socket neutral.
4. Install a fresh medium-base A19 LED bulb (9W–13W).
5. Flip breaker back ON and pull the light chain.

— **Victory (HALE-AG, 4-Star Lead)**
