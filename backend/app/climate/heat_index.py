"""Deterministic Heat Index Calculation Module
Implements the National Weather Service (NWS) / NOAA Rothfusz Regression Equation.
Reference: Steadman (1979) and Rothfusz (1990).
"""
import math
from typing import Tuple

def celsius_to_fahrenheit(c: float) -> float:
    return (c * 9.0 / 5.0) + 32.0

def fahrenheit_to_celsius(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0

def calculate_heat_index(temperature_c: float, relative_humidity_pct: float) -> Tuple[float, str]:
    """
    Computes apparent temperature (Heat Index) in Celsius and its risk category.
    Formula applies strictly to ambient temperature >= 20°C and RH between 0% and 100%.
    """
    t_c = max(-20.0, min(60.0, temperature_c))
    rh = max(0.0, min(100.0, relative_humidity_pct))
    
    # Below 20°C, apparent temperature equals ambient temperature
    if t_c < 20.0:
        return round(t_c, 2), "LOW"

    t_f = celsius_to_fahrenheit(t_c)
    
    # 1. Steadman simple formula
    hi_simple = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
    
    if hi_simple < 80.0:
        hi_f = hi_simple
    else:
        # 2. Full Rothfusz regression equation
        hi_f = (
            -42.379
            + 2.04901523 * t_f
            + 10.14333127 * rh
            - 0.22475541 * t_f * rh
            - 0.00683783 * t_f * t_f
            - 0.05481717 * rh * rh
            + 0.00122874 * t_f * t_f * rh
            + 0.00085282 * t_f * rh * rh
            - 0.00000199 * t_f * t_f * rh * rh
        )
        
        # Adjustments
        if rh < 13.0 and 80.0 <= t_f <= 112.0:
            adj = ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
            hi_f -= adj
        elif rh > 85.0 and 80.0 <= t_f <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
            hi_f += adj

    hi_c = fahrenheit_to_celsius(hi_f)
    
    # Categorization based on NWS guidelines
    # Caution: 27°C - 32°C (80°F - 90°F)
    # Extreme Caution: 32°C - 39°C (90°F - 103°F)
    # Danger: 39°C - 51°C (103°F - 124°F)
    # Extreme Danger: >= 51°C (>= 125°F)
    if hi_c < 27.0:
        category = "LOW"
    elif hi_c < 32.0:
        category = "CAUTION"
    elif hi_c < 39.0:
        category = "EXTREME_CAUTION"
    elif hi_c < 51.0:
        category = "DANGER"
    else:
        category = "EXTREME_DANGER"

    return round(hi_c, 2), category
