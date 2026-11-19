# Climate Methodology & Environmental Indicators

## 1. Overview & Scientific Boundaries

HeatLedger provides evidence of environmental conditions during outdoor gig work.
To maintain scientific credibility and avoid medical or legal overreach:
- **No Medical Diagnosis:** HeatLedger does not provide medical diagnoses or treatment recommendations.
- **No Automatic Legal Causation:** The platform correlates working periods with environmental observations, but never claims that heat statistically or legally caused a specific financial loss.
- **Transparent Attribution:** Every observation explicitly identifies the data provider, source station ID, spatial resolution, and timestamp.

---

## 2. Rothfusz Heat Index Equation (NWS / NOAA)

The Heat Index is an empirical calculation of apparent temperature based on ambient temperature ($T_a$ in °F) and relative humidity ($RH$ in %):

For temperatures where $T_a \ge 80^\circ\text{F}$ ($26.7^\circ\text{C}$) and $RH \ge 40\%$, the full Rothfusz regression equation is applied:

$$
\begin{aligned}
HI = &-42.379 + 2.04901523 \cdot T + 10.14333127 \cdot RH - 0.22475541 \cdot T \cdot RH \\
&- 0.00683783 \cdot T^2 - 0.05481717 \cdot RH^2 + 0.00122874 \cdot T^2 \cdot RH \\
&+ 0.00085282 \cdot T \cdot RH^2 - 0.00000199 \cdot T^2 \cdot RH^2
\end{aligned}
$$

### Risk Categories:
- **Low Risk:** $< 27^\circ\text{C}$
- **Caution:** $27^\circ\text{C} - 32^\circ\text{C}$ ($80^\circ\text{F} - 90^\circ\text{F}$)
- **Extreme Caution:** $32^\circ\text{C} - 39^\circ\text{C}$ ($90^\circ\text{F} - 103^\circ\text{F}$)
- **Danger (Severe Climate Stress):** $39^\circ\text{C} - 51^\circ\text{C}$ ($103^\circ\text{F} - 124^\circ\text{F}$)
- **Extreme Danger:** $\ge 51^\circ\text{C}$ ($\ge 125^\circ\text{F}$)

---

## 3. Simplified Wet-Bulb Globe Temperature (sWBGT) Proxy

Because direct field measurements of black-globe temperature and natural wet-bulb temperature are unavailable on mobile consumer devices, HeatLedger calculates an **estimated outdoor shade sWBGT proxy** based on the validated Australian Bureau of Meteorology (BOM) simplified model:

$$sWBGT = 0.567 \cdot T_a + 0.393 \cdot e + 3.94$$

Where $e$ is water vapor pressure in hPa, computed via Tetens equation:

$$e = \frac{RH}{100} \cdot 6.1078 \cdot \exp\left(\frac{17.27 \cdot T_a}{T_a + 237.3}\right)$$

> **Caveat:** HeatLedger explicitly labels this value as an **ESTIMATED PROXY**. Direct WBGT certification requires calibrated black-globe sensor instrumentation.

---

## 4. Spatiotemporal Matching Engine

Observations are matched to working shifts using strict thresholds:
- **Spatial Radius:** Maximum allowable distance to weather observation is **35.0 km**.
- **Temporal Window:** Maximum allowable time difference is **90 minutes**.
- **Quality Grades:**
  - **HIGH:** GPS sample available within 15 km and observation within 30 minutes.
  - **MEDIUM:** Match within 35 km and 90 minutes.
  - **ESTIMATED:** City-center baseline coordinate match.
