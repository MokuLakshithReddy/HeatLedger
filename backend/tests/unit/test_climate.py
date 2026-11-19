import pytest
from backend.app.climate.heat_index import calculate_heat_index, celsius_to_fahrenheit, fahrenheit_to_celsius
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy, calculate_vapor_pressure_hpa
from backend.app.climate.engine import haversine_distance_km

def test_heat_index_benchmarks():
    # Below 20°C ambient, apparent temp equals ambient temp (LOW)
    hi, category = calculate_heat_index(18.0, 50.0)
    assert hi == 18.0
    assert category == "LOW"

    # Moderate warm temperature: 30°C, 60% RH -> Caution / Extreme Caution
    hi_mod, cat_mod = calculate_heat_index(30.0, 60.0)
    assert hi_mod >= 32.0
    assert cat_mod in ["CAUTION", "EXTREME_CAUTION"]

    # Severe Indian pre-monsoon heatwave: 42°C, 45% RH -> Extreme Danger
    hi_extreme, cat_extreme = calculate_heat_index(42.0, 45.0)
    assert hi_extreme >= 45.0
    assert cat_extreme in ["DANGER", "EXTREME_DANGER"]

def test_wbgt_simplified_proxy_calculation():
    # 35°C ambient, 50% relative humidity
    vp = calculate_vapor_pressure_hpa(35.0, 50.0)
    assert 25.0 < vp < 35.0 # Typical vapor pressure in hPa

    swbgt = calculate_simplified_wbgt_proxy(35.0, 50.0)
    assert 28.0 < swbgt < 38.0

def test_haversine_distance():
    # Distance between Begumpet (17.4485, 78.4714) and Charminar (17.3616, 78.4747) in Hyderabad
    dist = haversine_distance_km(17.4485, 78.4714, 17.3616, 78.4747)
    # Begumpet to Charminar is approx 9.6 km
    assert 8.0 < dist < 12.0
