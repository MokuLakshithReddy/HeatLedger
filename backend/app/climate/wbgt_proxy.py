"""Estimated Wet-Bulb Globe Temperature (WBGT) Simplified Proxy Module
Based on the Australian Bureau of Meteorology (BOM) simplified formula (BOM, 2010).
Disclaimer: This is an estimated mathematical proxy based solely on ambient temperature
and water vapor pressure without direct solar radiation and wind globe thermometry measurements.
It is explicitly labeled as an ESTIMATED PROXY, not a direct laboratory/field sensor measurement.
"""
import math
from typing import Optional

def calculate_vapor_pressure_hpa(temperature_c: float, relative_humidity_pct: float) -> float:
    """
    Computes ambient water vapor pressure (e) in hPa using the Tetens formula.
    """
    t = temperature_c
    rh = max(0.0, min(100.0, relative_humidity_pct))
    # Saturation vapor pressure in hPa
    e_sat = 6.1078 * math.exp((17.27 * t) / (t + 237.3))
    # Actual vapor pressure
    return (rh / 100.0) * e_sat

def calculate_simplified_wbgt_proxy(
    temperature_c: float,
    relative_humidity_pct: float,
    wind_speed_mps: Optional[float] = None,
    solar_radiation_wm2: Optional[float] = None,
) -> float:
    """
    Calculates estimated outdoor shade WBGT proxy (°C).
    Formula: sWBGT = 0.567 * Ta + 0.393 * e + 3.94
    where:
      Ta = Dry bulb temperature (°C)
      e  = Water vapor pressure (hPa)
    """
    e = calculate_vapor_pressure_hpa(temperature_c, relative_humidity_pct)
    swbgt = 0.567 * temperature_c + 0.393 * e + 3.94
    return round(swbgt, 2)
