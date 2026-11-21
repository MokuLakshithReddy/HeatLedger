"""IMD (India Meteorological Department) Weather Provider Adapter
Official Portal: https://api.imd.gov.in/public/
API Reference: https://api.imd.gov.in/public/api_reference.html
Integrates with IMD station observations and AWS/ARG network when credentials are configured.
CLIM-02: Preserves actual observation timestamps returned by the source station.
"""
from datetime import datetime, timezone
import math
from typing import Optional, List, Dict, Any
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.providers.weather.base import BaseWeatherProvider, WeatherObservationDTO
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    return round(R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)

# Documented official IMD AWS / Observatory Stations
OFFICIAL_IMD_STATIONS = [
    {"station_id": "43128", "station_code": "43128", "station_name": "Begumpet AWS/Observatory (WMO 43128)", "lat": 17.4484, "lon": 78.4682},
    {"station_id": "43127", "station_code": "43127", "station_name": "Hyderabad Meteorological Centre (WMO 43127)", "lat": 17.4334, "lon": 78.4504},
    {"station_id": "43129", "station_code": "43129", "station_name": "Dundigal IAF Station", "lat": 17.5300, "lon": 78.4000},
    {"station_id": "43125", "station_code": "43125", "station_name": "Hakimpet Air Force Station", "lat": 17.5500, "lon": 78.5300},
    {"station_id": "43063", "station_code": "43063", "station_name": "Ramagundam Observatory", "lat": 18.7600, "lon": 79.5100},
    {"station_id": "43086", "station_code": "43086", "station_name": "Khammam AWS", "lat": 17.2500, "lon": 80.1500},
    {"station_id": "43150", "station_code": "43150", "station_name": "Nizamabad AWS", "lat": 18.6700, "lon": 78.1000},
    {"station_id": "43181", "station_code": "43181", "station_name": "Mahabubnagar AWS", "lat": 16.7300, "lon": 77.9800},
]

def find_nearest_imd_station(lat: float, lon: float) -> Dict[str, Any]:
    best = None
    min_dist = float("inf")
    for s in OFFICIAL_IMD_STATIONS:
        d = haversine_distance_km(lat, lon, s["lat"], s["lon"])
        if d < min_dist:
            min_dist = d
            best = s
    return best or OFFICIAL_IMD_STATIONS[0]

def parse_imd_record(data: Dict[str, Any], default_station: Dict[str, Any]) -> Optional[WeatherObservationDTO]:
    """Parses documented IMD API response schemas (current_wx and aws_data)."""
    # Documented IMD temperature field variants (CURR_TEMP, Temperature, TEMP, dry_bulb_temp)
    raw_temp = (
        data.get("CURR_TEMP")
        or data.get("Temperature")
        or data.get("TEMP")
        or data.get("temp_c")
        or data.get("dry_bulb_temp")
        or data.get("temperature")
    )
    # Documented IMD humidity field variants (Humidity, RH, humidity_percentage)
    raw_rh = (
        data.get("Humidity")
        or data.get("RH")
        or data.get("humidity_percentage")
        or data.get("humidity")
    )

    if raw_temp is None or raw_rh is None:
        logger.warning("IMD response missing mandatory TEMP or RH; returning None.")
        return None

    try:
        temp_c = float(raw_temp)
        rh_pct = float(raw_rh)
    except (ValueError, TypeError):
        return None

    hi_c, _ = calculate_heat_index(temp_c, rh_pct)

    # Documented IMD wind speed field variants (Wind Speed, WS, WS_KMPH)
    raw_ws = (
        data.get("Wind Speed")
        or data.get("WS")
        or data.get("wind_speed_mps")
        or data.get("wind_speed")
    )
    if raw_ws is None and data.get("wind_speed_kmph") is not None:
        wind_speed = round(float(data.get("wind_speed_kmph")) / 3.6, 1)
    elif raw_ws is None and data.get("WS_KMPH") is not None:
        wind_speed = round(float(data.get("WS_KMPH")) / 3.6, 1)
    else:
        try:
            wind_speed = float(raw_ws or 0.0)
        except (ValueError, TypeError):
            wind_speed = 0.0

    wbgt_c = calculate_simplified_wbgt_proxy(temp_c, rh_pct, wind_speed_mps=wind_speed)
    
    # CLIM-02: Documented IMD observation timestamps (single field or separate Date + Time)
    observed_at = None
    date_part = data.get("Date of Observation") or data.get("date")
    time_part = data.get("Time of Observation") or data.get("time")
    if date_part and time_part:
        try:
            date_str = str(date_part).strip()
            time_str = str(time_part).strip()
            if "/" in date_str:
                dt_obj = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            else:
                dt_obj = datetime.fromisoformat(f"{date_str}T{time_str}")
            observed_at = dt_obj.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    if not observed_at:
        obs_time_raw = (
            data.get("TIME_UTC")
            or data.get("TIMESTAMP")
            or data.get("date_time")
            or data.get("observed_at")
        )
        if obs_time_raw:
            try:
                observed_at = datetime.fromisoformat(str(obs_time_raw).replace("Z", "+00:00"))
            except Exception:
                pass

    if not observed_at:
        logger.warning("IMD observation missing verified source timestamp; rejecting unverified observation.")
        return None

    station_lat = data.get("LAT") or data.get("latitude") or data.get("lat")
    station_lon = data.get("LON") or data.get("longitude") or data.get("lon")
    if station_lat is not None and station_lon is not None:
        try:
            st_lat = float(station_lat)
            st_lon = float(station_lon)
        except (ValueError, TypeError):
            st_lat = default_station["lat"]
            st_lon = default_station["lon"]
    else:
        st_lat = default_station["lat"]
        st_lon = default_station["lon"]

    station_id = str(
        data.get("Station Name")
        or data.get("STATION_NAME")
        or data.get("station_name")
        or data.get("Station Id")
        or data.get("STATION_ID")
        or data.get("station_code")
        or default_station["station_name"]
    )

    return WeatherObservationDTO(
        provider_name="IMD",
        source_identifier=station_id,
        data_type="DIRECT_STATION_OBSERVATION",
        latitude=st_lat,
        longitude=st_lon,
        spatial_resolution_km=10.0,
        observed_at=observed_at,
        temperature_celsius=temp_c,
        relative_humidity_pct=rh_pct,
        heat_index_celsius=hi_c,
        wbgt_estimated_celsius=wbgt_c,
        wind_speed_mps=wind_speed,
        solar_radiation_wm2=float(data.get("solar_radiation", 0.0)) if "solar_radiation" in data else None,
        confidence_score=0.95,
        data_freshness_status="REALTIME",
        validation_status="VALIDATED",
        raw_payload=data,
    )

class IMDWeatherProvider(BaseWeatherProvider):
    def __init__(self):
        self.api_key = settings.IMD_API_KEY
        self.base_url = settings.IMD_BASE_URL.rstrip("/")
        self.timeout = 5.0 # Strict timeout

    @property
    def provider_name(self) -> str:
        return "IMD"

    async def get_current_observation(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherObservationDTO]:
        if not self.api_key:
            logger.info("IMD API key not configured; skipping live IMD fetch.")
            return None

        clean_base = self.base_url.rstrip("/")
        if clean_base.endswith("/api"):
            clean_base = clean_base[:-4]
        endpoint = f"{clean_base}/api/v1/current_wx"
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        
        station = find_nearest_imd_station(latitude, longitude)
        params = {
            "id": station["station_id"],
            "station_id": station["station_id"],
            "lat": str(latitude),
            "lon": str(longitude),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, headers=headers, params=params)
                # Fallback to aws_data if current_wx not present
                if response.status_code == 404:
                    response = await client.get(f"{clean_base}/api/v1/aws_data", headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0]

                    return parse_imd_record(data, station)
                else:
                    logger.warning(f"IMD returned HTTP {response.status_code}: {response.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"IMD provider request error: {str(e)}")
            return None

    async def get_observations_for_interval(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> List[WeatherObservationDTO]:
        if not self.api_key:
            return []

        clean_base = self.base_url.rstrip("/")
        if clean_base.endswith("/api"):
            clean_base = clean_base[:-4]
        endpoint = f"{clean_base}/api/v1/aws_data"
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        station = find_nearest_imd_station(latitude, longitude)
        params = {
            "id": station["station_id"],
            "sid": station["station_code"],
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, headers=headers, params=params)
                if response.status_code == 200:
                    records = response.json().get("observations", response.json() if isinstance(response.json(), list) else [])
                    out = []
                    for r in records:
                        dto = parse_imd_record(r, station)
                        if dto and start_time <= dto.observed_at <= end_time:
                            dto.data_freshness_status = "ARCHIVED_OBSERVATION"
                            out.append(dto)
                    return out
                return []
        except Exception as e:
            logger.error(f"IMD interval fetch error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"IMD interval fetch error: {str(e)}")
            return []

    async def check_health(self) -> Dict[str, Any]:
        """Verifies actual connectivity to IMD API portal."""
        if not self.api_key:
            return {
                "provider": self.provider_name,
                "configured": False,
                "status": "UNCONFIGURED",
                "disclaimer": "IMD Open Data API key not configured. Real-time observations unavailable.",
            }

        clean_base = self.base_url.rstrip("/")
        if clean_base.endswith("/api"):
            clean_base = clean_base[:-4]

        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{clean_base}/api/v1/health", headers=headers)
                if resp.status_code == 404:
                    resp = await client.get(f"{clean_base}/health", headers=headers)
                is_ok = resp.status_code in [200, 204]
                return {
                    "provider": self.provider_name,
                    "configured": True,
                    "status": "OPERATIONAL" if is_ok else f"DEGRADED_HTTP_{resp.status_code}",
                    "source": "India Meteorological Department (api.imd.gov.in)",
                }
        except Exception as e:
            return {
                "provider": self.provider_name,
                "configured": True,
                "status": "UNREACHABLE",
                "error": str(e),
                "source": "India Meteorological Department (api.imd.gov.in)",
            }

