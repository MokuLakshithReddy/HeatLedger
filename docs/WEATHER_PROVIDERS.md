# Meteorological Providers & Climate Ingestion Engine

HeatLedger correlates worker outdoor shifts with accredited meteorological observations to compute scientific occupational heat stress metrics.

---

## 1. Supported Weather Providers

### 1. India Meteorological Department (IMD)
- **Adapter:** `backend/app/providers/weather/imd.py`
- **Data Source:** Automatic Weather Stations (AWS) across Hyderabad (Begumpet Observatory, Hitec City AWS, Dundigal, Ramachandrapuram).
- **Provenance Preservation (CLIM-02):**
  - Observation timestamps from IMD stations are preserved exactly as reported by the sensor network.
  - Server ingestion time is recorded separately as an audit field (`ingested_at`).

### 2. Copernicus Climate Data Store (ERA5-Land)
- **Adapter:** `backend/app/providers/weather/era5.py`
- **Data Source:** ECMWF ERA5-Land hourly atmospheric reanalysis (0.1° / ~9km spatial resolution).
- **Physical Variables & Conversions (CLIM-01):**
  - 2m Temperature ($T_{2m}$): Converted from Kelvin ($K$) to Celsius ($^\circ\text{C}$):
    $$T_{^\circ\text{C}} = T_K - 273.15$$
  - Relative Humidity ($RH$): Derived from 2m temperature and 2m dewpoint temperature using the August-Roche-Magnus approximation:
    $$RH = 100 \times \exp\left(\frac{17.625 \times T_d}{243.04 + T_d} - \frac{17.625 \times T}{243.04 + T}\right)$$
  - Solar Radiation ($S$): Converted from integrated surface solar radiation downward (SSRD) in Joules ($J/\text{m}^2$) to flux rate ($W/\text{m}^2$).

---

## 2. Spatial & Temporal Correlation Limits (CLIM-03 & CLIM-04)

To prevent spurious environmental correlation, observations are strictly filtered:
- **Maximum Distance Threshold:** 25.0 km (Haversine geodesic distance from worker shift point to observation station). Observations farther than 25km are excluded.
- **Maximum Temporal Window:** 60 minutes (Time difference between shift interval and station observation timestamp).
- **Work vs. Rest Separation (CLIM-05):**
  - Break periods declared by the worker are excluded from active heat exposure totals.
