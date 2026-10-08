# How established running-time simulators model train movement, and what we're missing

Scope: metro to HSR. Date: 2026-10-08.

## 0. Method, evidence labels and caveats

- **[SRC]**: checked in source code or docs of open-source tools that I cloned (`git clone --depth 1`, read-only, nothing executed) under `scratchpad/ext/`:
  - Open Rails, C# physics: https://github.com/openrails/openrails (`Source/Orts.Simulation/Simulation/RollingStocks/...` and `Source/Documentation/Manual/physics.rst`, `operation.rst`)
  - TrainRuns.jl (railtoolkit): https://github.com/railtoolkit/TrainRuns.jl (`src/formulary.jl`, `src/TrainRuns.jl`, `src/behavior.jl`, `test/data/trains/*.yaml`)
  - OSRD, the open-source SNCF/OpenRail Association running-time and capacity tool: https://github.com/OpenRailAssociation/osrd (`core/envelope-sim`, `core/osrd-mp/.../envelope_sim`) and its docs repo https://github.com/OpenRailAssociation/osrd-website (`content/docs/explanation/...`, `content/docs/railway-wiki/...`, `static/pdf/MARECO.pdf`)
  - SUMO rail model: https://github.com/eclipse-sumo/sumo (`src/microsim/cfmodels/MSCFModel_Rail.h`)
- **[K]**: published domain knowledge (standards, textbooks, vendor documentation) that I could **not re-verify on the web in this session**. The shared WebSearch budget for this turn (200 calls across all agents) was already used up on my first query, and no web search succeeded. Treat [K] numbers as approximate and check them before using them as calibration constants. Proprietary tools (OpenTrack, RailSys, RAILSIM, RTC, FBS, LUKS, SIMONE) are described only from [K].
- **[EST]**: my own estimates. They come from a simple point-mass sensitivity model at `scratchpad/est/impact2.py` (my code, not from any of the repos) that runs four archetypes: metro (1 km between stops), commuter EMU (3.5 km), regional EMU and loco-hauled (12 km), and HSR (100 km). Each run includes one 1 km restriction at 50% of vmax. Appendix A has the results. They show sensitivity and order of magnitude, not calibrated predictions.

---

## 1. Simulators and what they model

| Tool | Type / origin | Train dynamics core | Traction / brake data | Adhesion / weather | Power supply | Signalling / braking curves | Driver / timetable features | Evidence |
|---|---|---|---|---|---|---|---|---|
| **OpenTrack** | Microscopic sync. simulation; ETH Zürich IVT spin-off (OpenTrack Railway Technology) | Time-step integration, mass-point or train-length grade averaging; Davis or Strahl/Sauthoff resistance | Tabulated F(v) per engine, multiple traction units, adhesion-limited TE; brake as constant decel or brake curves | Adhesion factor per run or scenario | Coupling to OpenPowerNet (co-simulation): voltage at pantograph feeds back to available TE | Fixed block, ETCS L1/L2/L3, CBTC, LZB/PZB, signal sighting and approach behaviour | "Performance" % per train for speed and TE, energy-saving runs (coasting, cruising), running-time supplements, Monte Carlo delays | [K] |
| **RailSys** (RMCon, Hannover) | Microscopic timetable construction and simulation (from Uni Hannover IVE) | Running-time calc per DB practice; train-length grade/curve averaging | Tabulated F(v), brake tables | Adhesion parameter | Optional energy module | Block/LZB/ETCS, blocking-time stairs | Allowances per DB rules (Regelzuschlag, Bauzuschlag), rounding to timetable grid, driver behaviour profiles | [K] |
| **RAILSIM X** (SYSTRA, ex-LTK) | TPC + network sim + traction power load flow | Time-step integration with Davis | Tabulated TE/DB curves, blended braking | Adhesion limits | Load-flow module: voltage-dependent TE, substation/feeder limits, regen receptivity | Fixed block, cab signalling speed codes, CBTC per IEEE 1474 | Performance levels (ATO), coasting, dwell | [K] |
| **RTC** (Berkeley Simulation Software) | North American network dispatch sim with TPC | Davis/AREMA resistance, train-length grade/curve effects | Locomotive TE tables (diesel notches, HEP) | Adhesion limit | No | ABS/CTC/PTC block logic | Dispatcher logic, train "performance" settings; heavily used for US capacity studies | [K] |
| **Open Rails** | Open-source driving simulator, C# | Per-car forces; Davis with low-speed (standstill) friction merge; per-car grade, curve and tunnel forces | Tabulated `MaxTractiveForceCurves`, dynamic-brake curves with fade, blending tables, detailed air-brake pipe model | **Curtius-Kniffler μ(v) × weather factor** (rain, snow, fog), random slippery spots, sanding, Polach/Pacha creep model | Line voltage, pantograph, circuit breaker, power-limitation selector (no load flow) | TCS scripts (ETCS-like) | AI "Efficiency" (performance %) scales max speed and accel/brake curves | **[SRC]** |
| **TrainRuns.jl** | Open-source minimum running-time calculator (TU Dresden heritage; Wende/Brünger formulas) | Mass-point or homogeneous strip; distance/time/velocity step | Tabulated F(v) pairs; constant brake decel | Constant μ = 0.2 (TODO comment in source) | No | No | Behaviour sections: breakFree, clearing, accelerating, cruising, diminishing, **coasting**, braking, halt | **[SRC]** |
| **OSRD** | Open-source SNCF / OpenRail Assoc. running time, capacity and STDCM | RK4 envelope simulation, train-length average grade; **min grade for braking**; ERA rotating-mass bounds | Effort curves **conditioned on mode, electrical-profile level, power-restriction code and comfort (AC/heating)** | Not explicit; ETCS Kdry/Kwet factors | **Electrical profiles** (along-track voltage classes select a TE curve), neutral sections with system times | **ETCS L2 EBD/SBD/GUI/IND curves per Subset-026**, LZB and PZB constant-decel models | **Driver behaviour offsets** (braking anticipation 100 m, accel postponement 50 m); **MARECO energy-optimal allowance** and linear allowance | **[SRC]** |
| **SUMO (rail CF model)** | Open-source microsim | Simple traction/resistance-table model | Tabulated F(v) and R(v) for ICE1, ICE3, RB425, NGT400, MireoPlus, etc. | No | No | Simplified | N/A | **[SRC]** |
| **FBS** (iRFP) | German timetable construction tool | Running-time calc per DB Fahrzeitenrechnung | Vehicle F(v) tables | Parameter | No | Blocking time | Rounding to 0.1 min internally and published to minutes, allowances | [K] |
| **DB Fahrzeitenrechnung** (RUT-K, DB internal) | Basis of DB Netz timetable running times | Wende/Brünger mechanics: Sauthoff/Strahl resistance, brake percentages (Bremshundertstel) | F(v) tables per Baureihe | Not in the minimum run | Not in the minimum run | LZB/PZB braking tables | **Regelzuschlag** (standard allowance, %) plus **Bauzuschlag** (works allowance), rounding | [K] |
| **Network Rail SRT method** | UK Sectional Running Times in Timetable Planning Rules | TPC-computed pass-to-pass SRTs per "timing load" | Class-specific | Not explicit; autumn TT variants | No | No | Half-minute rounding, start/stop additions, performance / engineering / pathing allowances | [K] |
| **SIMONE / FRISO / DONS** (NL) | Stochastic network sims (SIMONE: macroscopic, Incontrol; FRISO: microscopic, ProRail) | Running times are inputs (SIMONE) or simple dynamics (FRISO) | — | — | — | Block / headway | Stochastic dwell and running-time perturbations, running-time supplements (~5–7%) | [K] |
| **LUKS** (VIA Con, Aachen) | Capacity/timetable analysis | Running-time calc with train-dynamics module | F(v) tables | — | — | Blocking time, ETCS | Allowances, buffer times | [K] |
| **ERA ETCS braking curves simulation tool** | Reference implementation of Subset-026 §3.13 | Braking-curve calculation only | γ (lambda) or brake-percentage models, Kdry/Kwet, Kv, Kr, T_be, T_bs | M_NVAVADH | — | EBD/EBI/SBD/SBI/W/P/I/GUI | — | [K]; OSRD cites it for M_ROTATING bounds [SRC] |

---

## 2. Missing features, ranked by expected running-time impact

The ranking weighs the size of the effect and how widely it applies across metro, commuter, regional and HSR. Impacts are [EST] unless a source is given.

### Rank 1: Driver / ATO performance behaviour (performance %, cruising margin, anticipation offsets)

**What it is.** Real drivers and ATO do not run on the physical envelope. They (a) use less than full traction, (b) cruise a few km/h below the posted limit, (c) reach a lower limit *before* its start, (d) re-accelerate a little *after* the rear clears, and (e) brake below the planned maximum service rate. Production tools expose this as tunable parameters, and they use those parameters to calibrate against recorded runs.

**How tools model it.**
- OSRD `DriverBehaviour` [SRC, `core/envelope-sim/src/main/kotlin/fr/sncf/osrd/DriverBehaviour.kt`] shifts every MRSP (most restrictive speed profile) speed step:
  - `brakingAnticipationOffset = 100 m`: the lower limit is reached 100 m before the sign.
  - `acceleratingPostponementOffset = 50 m`: the train accelerates 50 m after the end of the restriction, on top of the train-length clearing.
  - These apply only on lineside-signalled lines (`signalingSystems = ["BAL","BAPR"]`), not under cab signalling.
- Open Rails AI `Efficiency` [SRC, `Manual/operation.rst` §"Default Performance and Performance Parameters"] multiplies max speed by the performance value, which "is used also to compute acceleration and braking curves".
- OpenTrack and RailSys have a per-train "performance" percentage on TE and speed, and some driver-behaviour profiles [K].
- OSRD's train-sim-v3 design doc says the problem directly: some users "want to reproduce existing timetables, which exhibit naive driver behaviour: aggressive accelerations, aggressive braking", while others want "somewhat realistic driver behaviour, with less aggressive acceleration and cautious braking" [SRC, `osrd-website/.../train-sim-v3/driver-behavior-modules.en.md`].

**Typical values.**
- Anticipation 100 m and postponement 50 m (OSRD default) [SRC].
- Performance 85–95% of TE [K/EST].
- Cruise margin 2–5 km/h below the limit [K/EST].
- Under ATO/CBTC, the ATO target is usually set 2–5 km/h below the ATP limit [K].

**Impact [EST, Appendix A].**

| Behaviour | Metro | Commuter | Regional | HSR |
|---|---|---|---|---|
| 90% TE plus 85% brake rate | +2.7% | +3.4% | +3.4% | +2.4% |
| Cruise 5 km/h under every limit | +7.6% | +3.6% | +2.2% | +1.1% |
| Anticipation offsets | — | — | — | +3–4 s per restriction (+1–5% on short metro hops) |

**Modes.** All modes, but this is the largest effect for metro and commuter.

**Implementation hint.** Add a `driver_profile` with `te_fraction`, `brake_fraction`, `cruise_margin_kmh`, `anticipation_m` and `postponement_m`. Default to the "timetable" profile (aggressive) and use a "realistic" profile for validation.

### Rank 2: Speed-dependent adhesion with weather/season states, for both traction and braking

**What it is.** μ falls with speed and with rail condition. On EMUs with many motored axles, dry adhesion rarely binds. On loco-hauled or diesel push-pull trains (adhesive mass about 20–25% of the train) it binds on wet rail, and in autumn it binds for everything, including braking, where drivers brake earlier and WSP extends distances.

**Formulas.**
- Curtius-Kniffler: μ = 7.5/(v + 44) + 0.161, with v in km/h. This is Open Rails' default. It gives 0.331 at standstill, 0.213 at 100 km/h and 0.183 at 300 km/h [SRC, `MSTSLocomotive.cs` `UpdateFrictionCoefficient()` L3502–3610, wagon constants L3577–3579; `physics.rst` §Adhesion].
- Kother: μ = 0.116 + 9/(v + 42) [K]. The `ORTSCurtius_Kniffler(A B C D)` parameters accept "Curtius-Kniffler, Kother or similar" [SRC physics.rst].

**Weather (Open Rails) [SRC].**
- Precipitation scales μ by 0.6–0.9: drizzle is worst, at 0.6, and heavy rain is better, at 0.9.
- Fog below 2 km visibility gives 0.6 + 2.75e-4·visibility_m, capped at 1.
- Random "slippery spots" 10–50 m long every 0–2 km set the factor to 0.6 or 0.8.
- The overall factor is clamped to 0.5–1.0.
- Sanding multiplies μ by 1.40 (clear), 1.25 (rain) or 1.50 (snow).

**Braking in low adhesion.** ETCS represents this with Kwet and M_NVAVADH: A_safe = Kdry·(Kwet + M_NVAVADH·(1 − Kwet))·A_emergency [SRC, OSRD `EtcsBrakeParams.getSafeBrakingAcceleration`, citing Subset-026 §3.13.6.2.1.4]. UK practice uses autumn timetables and defensive braking in leaf-fall season [K].

**Typical values [K].**

| Condition | μ |
|---|---|
| Dry, modern AC drive with slip control | 0.30–0.40 at standstill |
| Wet | about 0.6 × dry |
| Leaf contamination | 0.02–0.05 locally |

**Impact [EST].**

| Condition | Metro / commuter EMU | Loco-hauled regional | HSR |
|---|---|---|---|
| Wet rail (0.6 × CK, traction only) | +2% | **+10.9%** | +0.1% |
| Autumn (μ 0.10 plus brake rate × 0.6) | +15% | +29% | +5% |

**Modes.** Loco-hauled and diesel commuter/regional matter most; then EMU commuter and metro in autumn. For HSR, adhesion matters mainly in braking.

**Hint.** Our TE formula already has `adhesion·m_adh·g`. Make adhesion a function μ(v)·k_weather, and add a scenario switch {dry, wet, autumn} that also scales the planned service brake rate.

### Rank 3: Tabulated traction / brake curves and the real power available at the rail

**What it is.** All production tools use per-vehicle tabulated F(v) curves, linearly interpolated, rather than closed-form P/v formulas. These curves already include the motor current limit, field-weakening and high-speed fall-off (often steeper than 1/v), converter limits and gear limits. Curves differ by supply condition and auxiliary load.

**How tools model it.**
- OSRD `RJSEffortCurves` [SRC, `core/osrd-railjson/.../RJSEffortCurves.java`] holds a curve per traction mode (e.g., 25 kV, 1.5 kV, thermal). Each mode has conditional curves keyed by `electricalProfileLevel`, `powerRestrictionCode` and `comfort` ∈ {STANDARD, AIR_CONDITIONING, HEATING} [SRC, `PhysicsRollingStock.kt`]. Comfort curves represent HVAC power taken from the traction budget.
- Open Rails `MaxTractiveForceCurves`, `ORTSDieselTransmissionEfficiency` (rail power = engine power × η) [SRC, `MSTSDieselLocomotive.cs` L117, L244–301], and a diesel engine RPM ramp with default `ChangeUpRPMpS = 40` rpm/s [SRC, `DieselEngine.cs` L1763]. Going from idle to full RPM takes about 15–20 s, which delays full power after starting.
- Dynamic brake curve [SRC, `MSTSLocomotive.cs` L411–417, L678–690]: zero at `DynamicBrakeSpeed1` (default 5 km/h), max from `Speed2` (default 30 km/h), and a declining ratio at high speed.
- SUMO ICE3 table [SRC, `MSCFModel_Rail.h` L460–545]:

| Speed | 0 km/h | 100 km/h | 200 km/h | 300 km/h |
|---|---|---|---|---|
| Traction | 300 kN | 283 kN | 144 kN | 96 kN |
| Resistance | 7.4 kN | — | — | 71.8 kN |

  Mass is 420 t with ×1.04 rotating mass and a constant 0.5 m/s² brake. The residual acceleration at 300 km/h is only about 0.055 m/s², so small power errors produce large time errors near vmax.
- Other SUMO sets: RB425 is 138 t with 1.0 m/s² braking; MireoPlus B2T is 105.5 t with 1.1 m/s² [SRC].

**Typical values [K].**
- Diesel-electric transmission efficiency η is about 0.80–0.85.
- Head-end power (HEP) from the prime mover can take 300–800 kW from traction on US diesel push-pull.
- EMU auxiliaries and HVAC take about 3–8% of rated power.

**Impact [EST].** A 15% loss of rail power gives +0.8–2.0%. Losing 15% of both power and TE gives +2.9–4.9% (Appendix A). The effect is largest where trains run power-limited for a long time: regional, HSR, and diesel on grades.

**Modes.** All modes. This is critical for diesel push-pull, which is plausible for Cincinnati.

**Hint.** Accept a TE(v) table per consist with optional variants for supply level and auxiliary load. Model the diesel power ramp as a first-order lag (τ ≈ 5–10 s) or an RPM ramp on available power.

### Rank 4: Signalling-system braking supervision and ATP/ATO margins (ETCS, CBTC, LZB, PZB)

**What it is.** Under train protection, the driver or ATO does not brake on the train's own physics curve. It brakes on a supervised curve that has guaranteed (worst-case) deceleration, delay times and speed-measurement margins, so braking starts earlier and stops are reached more slowly.

**ETCS (Subset-026 §3.13), as implemented in OSRD [SRC, `envelope_sim/etcs/Constants.kt`, `EtcsBrakeParams.kt`, `ETCSBrakingCurves.kt`].**
- **EBD** uses A_safe = Kdry·(Kwet + M_NVAVADH(1 − Kwet))·A_emergency, with M_NVAVADH = 0 by default. Grade is taken as the **minimum grade under the train**. Rotating mass is bounded to M_ROTATING 2–15%.
- **EBI** is offset from EBD by:
  - traction cut-off time T_traction,
  - brake build-up time T_be (vDelta2 = A_EST_2·T_berem, with A_EST_2 = 0.4 m/s²),
  - speed-measurement uncertainty V_ura = 2 km/h at 30 km/h rising to 12 km/h at 500 km/h,
  - dV_ebi = 7.5 km/h at ≤ 110 km/h rising to 15 km/h at ≥ 210 km/h.
- **SBI** = EBI − v·T_bs; **Permitted** = SBI − v·T_driver (4 s); **Indication** = P − v·(max(0.8·T_bs, 5) + 4 s). Warning time T_WARNING = 2 s. National release speed is 40 km/h.
- The GUI (guidance) curve uses normal-service deceleration plus gradient correction factors kN+ and kN−.

**LZB [SRC, osrd-website `railway-wiki/signalling/spacing/ks/lzb`].** There are 12 constant-deceleration braking curves. Permitted-curve deceleration ranges from 0.08 to 0.79 m/s². Passenger choices by line speed and slope:

| Slope | ≤ 160 km/h | 160–250 km/h | 250–300 km/h |
|---|---|---|---|
| ≤ 5‰ | 0.57 m/s² | 0.51 m/s² | 0.45 m/s² |
| ≤ 12.5‰ | 0.51 m/s² | 0.45 m/s² | 0.39 m/s² |

Freight uses 0.33 or 0.27 m/s². Other LZB tools use a flat 0.5 (passenger) or 0.3 (freight).

**PZB [SRC, osrd-website `.../ks/pzb`].**

| Train type | Max speed | 1000 Hz supervision | 500 Hz supervision (within 153 m) | Restrictive mode |
|---|---|---|---|---|
| O | 165 km/h | 85 km/h after 23 s | 65 → 45 km/h | 1000 Hz limit 45 km/h |
| M | 125 km/h | 70 km/h after 29 s | 50 → 35 km/h | |
| U | 105 km/h | 55 km/h after 35 s | 40 → 25 km/h | |

Restrictive mode applies after a stop or after running below 10 km/h for 15 s. This matters for approaches to terminals and to signals at danger.

**CBTC (IEEE 1474.1) [K].**
- The safe-braking model is a worst-case sequence:
  1. Overspeed detection or reaction time.
  2. Propulsion removal; the train may keep accelerating at its runaway rate.
  3. Coast.
  4. Brake build-up.
  5. Guaranteed emergency brake rate (GEBR), reduced for downgrade.
- Position and speed uncertainty are added on top.
- Typical metro values: GEBR about 1.0–1.3 m/s²; total delays about 1.5–3 s.
- ATO runs below the ATP profile with a speed margin (2–5 km/h) and its own jerk-limited service brake.

**Impact [EST].**
- Cruise margin under ATP: see Rank 1 (+1–8%).
- Braking on ETCS Indication/Permitted curves instead of the driver's own curve: the offsets above add a v·(T_be + T_bs + 4 s + about 9 s) "front porch". At 300 km/h that is about 1–1.6 km. My estimate is +5–20 s per supervised speed reduction or stop at EoA for HSR, and +2–6 s per stop for metro CBTC.
- Under LZB/PZB, using the table decelerations instead of a vehicle service rate of 0.7–0.9 m/s² costs roughly +5–20 s per stop from 160 km/h.

**Modes.** Metro (CBTC), HSR (ETCS L2, LZB), and commuter on lines with cab signalling.

**Hint.** Add an optional `signalling` per segment that replaces the planned service brake curve with a supervised-curve deceleration and offsets, and that sets the ATO cruise margin.

### Rank 5: Power-supply limits (voltage drop, current limitation, electrical profiles, power-restriction codes)

**What it is.** At peak, or far from substations, line voltage sags. Traction converters limit current and therefore power: below a voltage threshold, the allowed current drops roughly linearly (EN 50388 current-limitation requirement [K]).

**Voltage limits (EN 50163) [K].**

| System | Nominal | Umin1 | Umin2 | Umax1 |
|---|---|---|---|---|
| 25 kV AC | 25 kV | 19 kV | 17.5 kV | 27.5 kV |
| 15 kV AC | 15 kV | 12 kV | — | — |
| 750 V DC | 750 V | 500 V | — | 900 V |
| 1500 V DC | 1500 V | 1000 V | — | — |
| 3 kV DC | 3 kV | 2 kV | — | — |

Available power scales roughly as U/U_n once current-limited. On 750 V DC metro, P can fall 15–30% at peak in weak sections.

**How tools model it.**
- RAILSIM and OpenTrack/OpenPowerNet run a full load flow [K].
- OSRD uses a lighter, precomputed approach [SRC]: **electrical profiles**, an along-track map of voltage "levels" (e.g., 25000 V, 22500 V, 20000 V classes for 25 kV, and lettered levels for 1.5 kV DC) that each select a different TE curve. Power-restriction codes are per-train/per-section caps. See `PhysicsRollingStock.mapTractiveEffortCurves(electrificationMap, comfort)` and `RJSElectricalProfileSet.kt`.
- Open Rails has only a fixed route `MaxLineVoltage` plus a `PowerLimitationSelector` [SRC, `ElectricPowerSupply.cs` L39, L71].

**Impact [EST].** Power −15% gives +0.8% (metro) to +2% (regional/HSR). If current-limited, so that TE also falls 15%, the range is +2.9% to +4.9%. Regenerative braking receptivity on DC affects energy, not time.

**Modes.** DC metro and light rail (largest), 25 kV commuter on long feeds, HSR on weak grids.

**Hint.** The cheap version is OSRD-style: a per-segment "supply factor" k_U(x) applied to P and optionally to TE. The full version would couple a DC/AC load flow.

### Rank 6: Speed-dependent service braking, brake blending and regen limits

**What it is.**
- Service braking is not constant over speed. At high speed, deceleration is limited by adhesion (μ falls with v), disc thermal capacity, and the electric brake's power limit: regen force ≈ P_brake/v above the base speed, and friction tops up under blending.
- Electrodynamic brakes fade at low speed. Open Rails defaults: zero at 5 km/h, full from 30 km/h [SRC].
- HSR often has eddy-current brakes for high-speed deceleration that is independent of adhesion [K].
- Train protection expresses this as γ(v) step curves (`SpeedIntervalValueCurve` in OSRD) [SRC].

**Typical values.**
- HSR service decel ≈ 0.3–0.45 m/s² above 230 km/h and 0.5–0.7 m/s² below 160 km/h [K/EST].
- Metro / commuter about 0.9–1.1 m/s² [K].
- SUMO uses a constant 0.5 m/s² for ICE3 and 1.0–1.1 m/s² for regional EMUs [SRC].

**Impact [EST].** For HSR, a speed-dependent curve (0.35 above 230 km/h, 0.45 for 160–230 km/h, 0.6 below) instead of a constant 0.6 costs +13 s over two decelerations, about +0.9% of a 100 km run. A single analytic stop from 300 km/h at 0.4 instead of 0.6 m/s² costs about +35 s.

**Modes.** HSR and fast regional.

**Hint.** Make the planned service rate a table b(v). Keep the jerk limit and build-up delay we already have.

### Rank 7: Terminal / platform approach behaviour and stopping position

**What it is.**
- Approaches to terminal stub platforms are slow: typically 15–40 km/h in the last 100–300 m because of buffer stops, PZB restrictive curves [SRC above] and UK approach-to-buffer-stops practice [K].
- Platform stop position: the head stops at a stop marker for the train length, usually near the far end of the platform, not at the platform centroid [K]. OSRD stops the head at the stop location [SRC: `TrainPhysicsIntegrator`/envelope stops at path offsets].
- Turnback: changing ends takes 2–4 min crewed or about 90–120 s for driverless or step-back crews [K/EST]. HSR minimum turnaround is about 15–20 min [K].

**Impact [EST].** A 30 km/h limit over the last 200 m adds 5–15 s per terminal arrival (+1–6.5% of the final leg). Stopping position can move effective inter-station distance by up to (L_platform − L_train)/2. For a 300 m platform and a 150 m train that is 75 m, about 3–5 s per stop for commuter trains.

**Modes.** Commuter, regional and metro (termini). HSR termini get the same absolute penalty, which is small in percentage terms.

### Rank 8: Neutral sections, phase breaks and system changeovers

**What it is.** Electric trains must cut traction between the announcement/execution signs and the end sign. They then need "system times" to restore traction: a few seconds for traction resumption and tens of seconds if the pantograph is lowered.

**OSRD model [SRC, osrd-website `explanation/models/neutral_sections`].**
- Coasting starts when the head passes the **announcement** sign.
- System times start when the head passes the end sign.
- The coast is extended by v_exit × system_time.
- Each neutral section is directional and carries a `lower_pantograph` flag.

**Typical values [K/EST].**
- 25 kV phase breaks at substations and mid-point sectioning posts, roughly every 20–30 km.
- Physical gap 30–400 m; coast region including signs 300–600 m.
- System time 3–10 s, or 20–60 s with pantograph lowering at a voltage changeover.

**Impact [EST].**
- At HSR cruise the loss is negligible: about 0.2 s, since deceleration from resistance alone is about 0.05–0.15 m/s².
- If the section falls in an acceleration zone near a station or on an upgrade, the loss is +6–14 s each (commuter/regional, Appendix A).
- Dual-voltage changeovers with pantograph lowering cost 20–60 s each.

**Modes.** 25 kV commuter and regional (placement-dependent), dual-system trains.

### Rank 9: Passenger load (AW0–AW3) and load-weigh compensation

**What it is.** Mass rises with passengers.
- US AW classes [K]: AW0 empty, AW1 seated, AW2 seated plus about 4 standees/m², AW3 crush at about 6 standees/m².
- Passenger mass about 70–80 kg [K].
- Metro/EMU propulsion often compensates load (constant acceleration up to AW2 or AW3) until the power limit. Braking is load-compensated through load-weigh valves.

**Impact [EST].** +20% mass without compensation gives +2.2% (metro), +2.6–2.7% (commuter/regional) and +2% (HSR). With compensation below about 40 km/h, roughly half of that.

**Modes.** Metro and commuter at peak (largest); regional and HSR minor.

### Rank 10: Allowance distribution (MARECO / linear) and timetable rounding conventions

**What it is.** We already add padding as a percentage plus final-leg recovery. Production tools also decide **where** the padding is consumed, which changes intermediate passing and arrival times and the energy used. They also round to a timetable grid.

**MARECO [SRC, OSRD `allowances/MarecoAllowance.kt`; `static/pdf/MARECO.pdf`, Lancien & Fontaine, RGCF Nov 1981].**
- MARECO is SNCF's energy-optimal allowance distribution. A binary search finds a speed cap v1.
- Coasting phases are placed before braking points and before accelerating slopes. Coasting ends at
  vf = W·v1 / (W + R(v1)·v1), where W = v1²·R′(v1).
- Rationale from the paper: the marginal energy gain per second of added time, −dE/dt, should be equal everywhere. For constant-speed running, −dE/dt = R′·V².
- The 1981 paper says SNCF's earlier computer method (HORER) uniformly increased elementary running times by **5, 7.5 or 10%**. It also says a uniform n% slowdown saves roughly 2n% of traction energy.

**Linear distribution [SRC, OSRD docs].** Speeds are scaled uniformly. OSRD separates a *regularity* allowance (whole route) from a *construction* allowance (local).

**Standard allowance values [K].**
- UIC leaflet 451-1 recommends a time-based percentage of roughly 3–7% (rising with speed and train mass), plus about 1–1.5 min/100 km for faster trains.
- DB uses a Regelzuschlag of about 3–7% for passenger trains depending on traction and speed, plus a Bauzuschlag for engineering works.
- NS/ProRail uses about 5–7%.
- Network Rail adds **performance, engineering and pathing allowances** on top of SRTs. SRTs are in half-minutes, with separate start and stop additions per timing point.
- WTT resolution is 30 s; public times are whole minutes.

**Energy-efficient driving literature [K].** Howlett & Pudney optimal control gives the sequence max-accel → cruise → coast → max-brake. Reviews (e.g., Scheepmaker, Goverde & Kroon 2017) report 10–25% energy savings for 3–10% extra running time.

**Impact.** Not a running-time error once padding is fixed, but it moves intermediate times by tens of seconds. Rounding adds 0–30 s per timing point, depending on whether it rounds up or to nearest [EST].

**Modes.** All modes; DAS/ATO coasting matters most for metro and regional.

### Rank 11: Turnout / junction speeds by turnout geometry

**What it is.** Diverging-route speed limits come from the turnout radius or number, not from cant deficiency on the polyline. These limits often dominate station throats and junctions.

**Typical tables [K, approximate; confirm against the railroad timetable or special instructions].**

| Turnout | Diverging speed |
|---|---|
| DB EW 190-1:9 | 40 km/h |
| DB EW 300-1:9 | 50 km/h |
| DB EW 500-1:12 | 60 km/h |
| DB EW 760-1:14 | 80 km/h |
| DB EW 1200-1:18.5 | 100 km/h |
| DB EW 2500-1:26.5 | 130 km/h |
| DB clothoid 1:42 | 160 km/h |
| DB clothoid 1:65 | 200–220 km/h |
| US AREMA #8 | ~15 mph |
| US AREMA #10 | 20–25 mph |
| US AREMA #15 | 30 mph |
| US AREMA #20 | 40–45 mph |
| US AREMA #24 | 50 mph |
| US AREMA #32.7 | ~60–80 mph |

**Impact [EST].** Using #10 (25 mph) instead of #20 (45 mph) for a 150 m train through a 200 m interlocking costs about 15–25 s per occurrence including decel and accel.

**Modes.** Commuter and regional (Cincinnati junction and station throats); metro crossovers at termini.

### Rank 12: Aerodynamics refinements (wind allowance, per-car aero, blockage-dependent tunnel drag, crosswind)

- **Headwind allowance.** TrainRuns.jl uses Δv_air = 15 km/h in the aerodynamic term, f_R2·((v + Δv_air)/v00)², per Sauthoff/Wende [SRC, `src/TrainRuns.jl` L21, `src/formulary.jl`].
  - Passenger coaches use Sauthoff: F = m·g·(f0 + f1·v/v00 + f2·((v + Δv)/v00)²), with v00 = 100 km/h.
  - Freight uses Strahl: F = m·g·(f0 + f2·(v/v00)²).
  - Example coefficients from the repo [SRC, from Wende 2003 p.151–153]: double-deck coaches f0 2.0‰, f1 0.715‰, f2 3.64‰; local EMU 3.0/1.4/3.9‰; TRAXX loco f0 2.5‰, f2 6.0‰; freight wagons f0 1.4‰, f2 3.9‰.
  - Impact [EST]: +0.1–0.3% of running time (+3 s per 100 km on HSR).
- **Per-car aero / train-length scaling** [K]: F_aero = ½ρA·v²·(C_nose + C_tail + λ·L/D_h). A Davis C that is not scaled with consist length misstates resistance for variable-length consists. Relevant if consists vary (e.g., 4-car vs 8-car).
- **Tunnel drag as a function of blockage ratio and tunnel length.** Open Rails [SRC, `TrainCar.cs` `UpdateTunnelForce()` L1336–1385; `physics.rst` "Calculation of Tunnel Resistance", source: Sirong Yi et al.] uses:
  - W_t = (A·L_tr/(P + G))·v²·(1 − 1/(1 + √((B + C(L_t − L_tr))/L_tr)))²
  - A = 3.318e-5·ρ·F_t/(1 − F_tr/F_t)², B = 174.419·(1 − F_tr/F_t)², C = 2.907·(1 − F_tr/F_t)²/(4F_t/R_t)
  - Default tunnel sections by route speed (single / double track): 21 / 41.8 m² below 120 km/h; 42 / 76 m² for 120–160; 50 / 80 m² for 160–200; 58 / 90 m² for 200–250; 70 / 100 m² above 250 km/h.
  - Note: the code multiplies the per-kN value by mass in tonnes, which looks low by a factor of g. With ×9.81, an ICE-like train at 300 km/h in a 70 m² tunnel gets about +45 kN against about 55 kN open-air aero, i.e. tunnel factor ≈ 1.8 [EST]. Our constant tunnel factor on C is fine if it is chosen per tunnel class.
- **Crosswind** [SRC, `MSTSWagon.cs` `UpdateWindForce()` L3287–3400]: Open Rails models resultant air speed √(v² + w² + 2vw·cosθ) for drag, plus a lateral flange-friction term. Negligible for scheduling.

**Modes.** HSR (minor), long tunnels.

### Rank 13: Starting resistance, bearing temperature and speed-dependent curve resistance (low impact)

- Open Rails starting/breakaway resistance [SRC, `MSTSWagon.cs` L2770–2830; `physics.rst` §Davis]:
  - Below `ORTSMergeSpeed` (about 5 mph) friction blends linearly from standstill friction to the Davis value.
  - Starting resistance by bearing type (AREMA, per short ton): roller 5 lb/ton above freezing and 15 below; journal 25 and 35.
  - Bearing temperature scales Davis A by up to ×1.3 at −10 °C.
- Open Rails curve resistance [SRC, `TrainCar.cs` `UpdateCurveForce()` L2285]:
  - F = m·g·μ_w·(gauge + rigid wheelbase)/(2R) + 1.5·|v²/R − g·h/gauge| kgf/t.
  - This is speed-dependent with a minimum at the balancing speed, unlike Röckl.
- OSRD uses the SNCF rule that equivalent curve grade = 800/R ‰ [SRC, osrd-website physical_modeling].
- Impact [EST]: under 0.5% except for heavy diesel starts on grades in winter.

### Rank 14: Stochastic running-time variation (for validation and robustness)

- SIMONE/FRISO and OpenTrack apply random perturbations to running and dwell times, then evaluate punctuality distributions [K]. Typical approach: a running-time multiplier drawn from a fitted distribution (e.g., log-normal, 1–3% CV) per train run, and a performance % per driver [K/EST].
- This is useful for converting our deterministic times into the 85th-percentile times that SRT practice targets [K].

---

## 3. Validation approaches these tools use

1. **Recorded-run comparison (speed–distance profiles)** [K].
   - OpenTrack, RailSys, RAILSIM and RTC users calibrate against on-train monitoring recorder (OTMR) or event-recorder data, or GPS/ATO logs: speed vs distance, time at timing points, energy at the pantograph.
   - Tolerance targets in practice [K]:
     - Running time within ±2–3% per section (some specs ±5%) for minimum-time runs, after calibrating driver performance %.
     - Traction energy within ±5–10%.
   - Typical calibration knobs: performance %, adhesion, brake rate, and Davis coefficients from coast-down tests.
2. **Statistical comparison with operational data** [K].
   - Network Rail and DB compare SRTs and timetable times with train describer, TRUST or LeiDis data.
   - Common targets: the median actual time should sit inside the SRT, and the allowance should cover roughly the 85th–90th percentile.
   - Dutch practice compares SIMONE punctuality outputs against realized punctuality.
3. **Reference-implementation comparison** for braking curves [K/SRC].
   - The ERA ETCS braking-curves simulation tool is the reference for Subset-026 curves. OSRD cites "ERA braking curves simulation tool v5.1" for its rotating-mass constants [SRC, `PhysicsRollingStock.getGradientAcceleration`].
4. **Snapshot / regression tests.** TrainRuns.jl uses dataframe snapshot tests over trains × paths (`test/highlevel_test.jl`) [SRC]. These check stability between versions, not physical accuracy.
5. **Physics sanity tests** [K/EST].
   - Coast-down tests to fit Davis A, B and C.
   - Standing-start acceleration tests: time to 50/100 km/h against the manufacturer's performance curve.
   - Brake-test stopping distances against the rolling stock's braked weight / brake-percentage tables.
6. **Suggested target for us [EST].** For each mode, match published schedules or recorded runs to within ±3% per inter-station segment and ±2% end-to-end, after a single per-mode calibration of driver performance % and cruise margin. Report residuals separately for acceleration, cruise and braking phases so errors are attributable.

---

## Appendix A: Sensitivity estimates [EST]

Script: `scratchpad/est/impact2.py` (my code). Point-mass model with Davis resistance, TE = min(μ·m_adh·g, TE_max, P/v), a constant planned brake rate, and one 1 km restriction at 50% vmax. Baseline μ is a constant 0.25. The table shows Δ running time against baseline (seconds and %).

| Scenario | Metro, 1 km (base 85.6 s) | Commuter, 3.5 km (183 s) | Regional EMU, 12 km (384 s) | Loco-hauled regional, 12 km (402 s) | HSR, 100 km (1436 s) |
|---|---|---|---|---|---|
| Curtius-Kniffler dry vs const 0.25 | 0 | 0 | 0 | +0.7 s | 0 |
| Wet rail 0.6×CK (traction) | +1.7 s (2.0%) | +3.6 s (2.0%) | +4.0 s (1.0%) | **+43.6 s (10.9%)** | +1.5 s (0.1%) |
| Autumn μ = 0.10 plus brake × 0.6 | +13.3 s (15.5%) | +28.1 s (15.4%) | +44.9 s (11.7%) | +116 s (28.9%) | +76.7 s (5.3%) |
| Driver 90% TE, 85% brake | +2.3 s (2.7%) | +6.2 s (3.4%) | +12.9 s (3.4%) | +10.6 s (2.6%) | +34.6 s (2.4%) |
| Anticipate 100 m / postpone 50 m | +4.2 s (4.9%) | +3.3 s (1.8%) | +3.4 s (0.9%) | +3.3 s (0.8%) | +1.8 s (0.1%) |
| Cruise 5 km/h under limits | +6.5 s (7.6%) | +6.6 s (3.6%) | +8.4 s (2.2%) | +8.5 s (2.1%) | +16.0 s (1.1%) |
| Supply: power −15% | +0.7 s (0.8%) | +2.4 s (1.3%) | +7.5 s (2.0%) | +4.2 s (1.0%) | +25.6 s (1.8%) |
| Supply: power and TE −15% | +2.5 s (2.9%) | +6.7 s (3.7%) | +18.9 s (4.9%) | +10.7 s (2.7%) | +66.5 s (4.6%) |
| Load +20%, no compensation | +1.9 s (2.2%) | +4.8 s (2.6%) | +10.2 s (2.7%) | +4.4 s (1.1%) | +29.0 s (2.0%) |
| Headwind allowance 15 km/h | ≈0 | +0.2 s | +0.8 s | +0.5 s | +3.1 s (0.2%) |
| Neutral section near start / at HSR cruise | +0.1 s | +6.4 s (3.5%) | +9.4 s (2.4%) | +13.5 s (3.4%) | +0.2 s |
| Speed-dependent HSR brake vs const 0.6 | — | — | — | — | +13.1 s (0.9%) |
| Terminal approach 30 km/h last 200 m | +4.9 s (5.7%) | +11.9 s (6.5%) | +14.3 s (3.7%) | +13.5 s (3.4%) | +15.2 s (1.1%) |

Archetype parameters:

| Archetype | Mass | Max TE | Power | Max speed | Brake rate |
|---|---|---|---|---|---|
| Metro | 230 t | 330 kN | 3 MW | 80 km/h | 1.0 m/s² |
| Commuter | 300 t | 300 kN | 4 MW | 130 km/h | 0.8 m/s² |
| Regional EMU | 300 t | 300 kN | 4 MW | 160 km/h | 0.7 m/s² |
| Loco-hauled regional | 380 t (85 t adhesive) | 300 kN | 5.6 MW | 160 km/h | 0.6 m/s² |
| HSR | 420 t | 300 kN | 8 MW | 300 km/h | 0.6 m/s² |

Davis coefficients are generic. The jerk limit and brake build-up delay are omitted, so absolute times are optimistic, but the deltas are indicative.

## Appendix B: Key source locations (cloned repos)

- Open Rails:
  - `Source/Orts.Simulation/Simulation/RollingStocks/MSTSLocomotive.cs`: adhesion and weather L3502–3610; dynamic brake L411–435 and L678–690; power/current limits L141–146 and L2046–2047.
  - `.../TrainCar.cs`: tunnel defaults L836–910; tunnel force L1336–1385; curve force L2285–2310.
  - `.../MSTSWagon.cs`: low-speed friction and bearing temperature L2770–2830; wind L3287–3400.
  - `.../MSTSDieselLocomotive.cs`: transmission efficiency L117 and L244–301.
  - `.../SubSystems/PowerSupplies/DieselEngine.cs`: RPM ramp L646–654 and L1532–1536; default L1763.
  - `.../SubSystems/PowerTransmissions/Axle.cs`: Polach/Pacha switch L478–494.
  - `Source/Documentation/Manual/physics.rst`: adhesion ~L201–360; tunnel L5057–5220; curve L4517+.
  - `Source/Documentation/Manual/operation.rst`: L603–633 (AI efficiency).
- TrainRuns.jl:
  - `src/formulary.jl`: Sauthoff/Strahl resistance, step equations, braking.
  - `src/TrainRuns.jl` L19–21: g, μ = 0.2, Δv_air = 15 km/h.
  - `src/behavior.jl`: behaviour sections, including coasting at L1288.
  - `test/data/trains/*.yaml`: Wende/Hansen coefficients and rotating-mass values 1.03–1.09.
- OSRD:
  - `core/envelope-sim/src/main/kotlin/fr/sncf/osrd/DriverBehaviour.kt`
  - `core/osrd-mp/src/commonMain/kotlin/fr/sncf/osrd/envelope_sim/TrainPhysicsIntegrator.kt`: RK4; average grade for traction, min grade for braking.
  - `.../envelope_sim/PhysicsRollingStock.kt`: effort curves by electrical condition and comfort; rotating-mass gradient term.
  - `.../envelope_sim/etcs/Constants.kt`, `EtcsBrakeParams.kt`
  - `core/envelope-sim/.../envelope_sim/etcs/ETCSBrakingCurves.kt`
  - `.../allowances/MarecoAllowance.kt`, `LinearAllowance.kt`
  - `core/osrd-railjson/.../rollingstock/RJSEffortCurves.java`
- osrd-website: `content/docs/explanation/models/neutral_sections/index.en.md`, `.../running_time_calculation/allowances/index.en.md`, `.../physical_modeling/index.en.md`, `content/docs/railway-wiki/signalling/spacing/ks/{lzb,pzb}/_index.en.md`, `content/docs/reference/design-docs/train-sim-v3/driver-behavior-modules.en.md`, `static/pdf/MARECO.pdf`
- SUMO: `src/microsim/cfmodels/MSCFModel_Rail.h`: ICE3 L460–545, RB425 L754+, MireoPlus L814+.
