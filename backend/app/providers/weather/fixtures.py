"""Demonstration Weather Provider for Hyderabad, Telangana
Provides realistic, high-fidelity meteorological fixtures for Hyderabad.
Stations modeled:
1. Begumpet (17.4485°N, 78.4714°E) - Urban Core / Weather Observatory
2. Gachibowli / Hitec City (17.4401°N, 78.3489°E) - Western IT & Logistics Corridor
3. Charminar / Old City (17.3616°N, 78.4747°E) - Dense Commercial & Outdoor Market Zone
4. Shamshabad / RGIA (17.2403°N, 78.4294°E) - Airport Suburban Station

All outputs are strictly labeled with data_freshness_status='DEMO_SAMPLE'
and validation_status='FALLBACK' to ensure complete transparency.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import math
from backend.app.providers.weather.base import BaseWeatherProvider, WeatherObservationDTO
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy

HYDERABAD_STATIONS = [
    {"id": "DEMO_HYD_BEGUMPET", "name": "Begumpet Observatory", "lat": 17.4485, "lon": 78.4714},
    {"id": "DEMO_HYD_GACHIBOWLI", "name": "Gachibowli Logistics Hub", "lat": 17.4401, "lon": 78.3489},
    {"id": "DEMO_HYD_CHARMINAR", "name": "Charminar Old City", "lat": 17.3616, "lon": 78.4747},
    {"id": "DEMO_HYD_AIRPORT", "name": "Shamshabad Outer Ring", "lat": 17.2403, "lon": 78.4294},
]

def find_nearest_demo_station(lat: float, lon: float) -> Dict[str, Any]:
    best = HYDERABAD_STATIONS[0]
    best_dist = 1e9
    for st in HYDERABAD_STATIONS:
        d = math.hypot(lat - st["lat"], lon - st["lon"])
        if d < best_dist:
            best_dist = d
            best = st
    return best

def simulate_hyderabad_temperature(hour_utc: float) -> Tuple[float, float, float]:
    # Hyderabad is UTC + 5:30 (IST).
    # Peak heat occurs at 14:00 - 15:30 IST (08:30 - 10:00 UTC) reaching 41-43°C during pre-monsoon heatwaves.
    # Minimum temperature occurs at 05:00 IST (23:30 UTC) around 28-30°C.
    hour_ist = (hour_utc + 5.5) % 24.0
    
    # Diurnal sinusoidal model
    angle = (hour_ist - 14.5) * (2.0 * math.pi / 24.0)
    temp = 35.0 + 7.5 * math.cos(angle) # Range: 27.5°C to 42.5°C
    
    # Relative humidity is inversely proportional to temperature
    rh = 55.0 - 25.0 * math.cos(angle) # Range: 30% to 80%
    
    wind = 3.5 + 1.5 * math.sin(angle)
    return round(temp, 1), round(rh, 1), round(wind, 1)

class HyderabadDemoProvider(BaseWeatherProvider):
    @property
    def provider_name(self) -> str:
        return "DEMO_HYDERABAD"

    async def get_current_observation(
        self, latitude: float, longitude: float
    ) -> WeatherObservationDTO:
        now = datetime.now(timezone.utc)
        station = find_nearest_demo_station(latitude, longitude)
        temp_c, rh_pct, wind_mps = simulate_hyderabad_temperature(now.hour + now.minute / 60.0)
        
        hi_c, _ = calculate_heat_index(temp_c, rh_pct)
        wbgt_c = calculate_simplified_wbgt_proxy(temp_c, rh_pct)

        return WeatherObservationDTO(
            provider_name=self.provider_name,
            source_identifier=station["id"],
            latitude=station["lat"],
            longitude=station["lon"],
            spatial_resolution_km=5.0,
            observed_at=now,
            temperature_celsius=temp_c,
            relative_humidity_pct=rh_pct,
            heat_index_celsius=hi_c,
            wbgt_estimated_celsius=wbgt_c,
            wind_speed_mps=wind_mps,
            solar_radiation_wm2=750.0 if 6 <= (now.hour + 5.5) % 24 <= 18 else 0.0,
            confidence_score=0.90,
            data_freshness_status="DEMO_SAMPLE",
            validation_status="FALLBACK",
            raw_payload={"station_name": station["name"], "city": "Hyderabad", "state": "Telangana"},
        )

    async def get_observations_for_interval(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> List[WeatherObservationDTO]:
        station = find_nearest_demo_station(latitude, longitude)
        observations = []
        
        # Step in 1-hour increments
        current = start_time
        while current <= end_time:
            temp_c, rh_pct, wind_mps = simulate_hyderabad_temperature(current.hour + current.minute / 60.0)
            hi_c, _ = calculate_heat_index(temp_c, rh_pct)
            wbgt_c = calculate_simplified_wbgt_proxy(temp_c, rh_pct)
            
            obs = WeatherObservationDTO(
                provider_name=self.provider_name,
                source_identifier=station["id"],
                latitude=station["lat"],
                longitude=station["lon"],
                spatial_resolution_km=5.0,
                observed_at=current,
                temperature_celsius=temp_c,
                relative_humidity_pct=rh_pct,
                heat_index_celsius=hi_c,
                wbgt_estimated_celsius=wbgt_c,
                wind_speed_mps=wind_mps,
                solar_radiation_wm2=700.0 if 6 <= (current.hour + 5.5) % 24 <= 18 else 0.0,
                confidence_score=0.90,
                data_freshness_status="DEMO_SAMPLE",
                validation_status="FALLBACK",
                raw_payload={"station_name": station["name"], "synthetic": True},
            )
            observations.append(obs)
            current += timedelta(hours=1)
            
        return observations

    async def check_health(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "status": "OPERATIONAL",
            "is_live": False,
            "region": "Hyderabad, Telangana (Urban + IT Corridor Stations)",
            "disclaimer": "Validated synthetic demonstration fixtures for Hyderabad weather conditions.",
        }
