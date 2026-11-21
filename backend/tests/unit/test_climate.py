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

def test_imd_station_resolution_and_parsing():
    from backend.app.providers.weather.imd import find_nearest_imd_station, IMDWeatherProvider
    from datetime import datetime, timezone

    # Coordinate near Begumpet Hyderabad resolves to Begumpet station
    st = find_nearest_imd_station(17.448, 78.468)
    assert st["station_id"] == "43128"
    assert "Begumpet" in st["station_name"]

    # Test parser behavior with official IMD fields
    provider = IMDWeatherProvider()
    assert provider.provider_name == "IMD"

def test_era5_land_parsing_and_multi_day_payload():
    from backend.app.providers.weather.era5 import ERA5LandProvider, kelvin_to_celsius, calculate_rh_from_dewpoint
    from datetime import datetime, timezone

    provider = ERA5LandProvider()
    assert provider.provider_name == "ERA5_LAND"

    # Test conversion
    c = kelvin_to_celsius(310.15) # 37°C
    assert abs(c - 37.0) < 0.1

    rh = calculate_rh_from_dewpoint(35.0, 25.0)
    assert rh is not None
    assert 45.0 < rh < 65.0

    # Parse response without fabricated fallbacks
    sample_response = {
        "series": [
            {
                "time": "2026-05-15T12:00:00Z",
                "2m_temperature": 313.15, # 40°C
                "2m_dewpoint_temperature": 298.15, # 25°C
                "10m_u_component_of_wind": 2.5,
                "10m_v_component_of_wind": 1.5,
            }
        ]
    }
    parsed = provider.parse_era5_response(sample_response, 17.38, 78.48, datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc))
    assert len(parsed) == 1
    obs = parsed[0]
    assert abs(obs.temperature_celsius - 40.0) < 0.1
    assert obs.heat_index_celsius is not None
    assert obs.heat_index_celsius > 45.0 # High heat index
    assert obs.data_type == "GRIDDED_REANALYSIS"

    # Test strict bounding with end_time
    bounded = provider.parse_era5_response(
        sample_response,
        17.38,
        78.48,
        base_time=datetime(2026, 5, 15, 13, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 5, 15, 15, 0, tzinfo=timezone.utc),
    )
    # The record at 12:00 is outside [13:00, 15:00], so it must be excluded
    assert len(bounded) == 0
