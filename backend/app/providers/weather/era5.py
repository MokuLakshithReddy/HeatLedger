"""Copernicus Climate Data Store (CDS) - ERA5-Land Reanalysis Adapter
Documentation: https://cds.climate.copernicus.eu/
ECMWF Confluence: https://confluence.ecmwf.int/display/CKB/ERA5-Land
Dataset: reanalysis-era5-land
Spatial Resolution: 0.1° x 0.1° (~9 km grid spacing at equator)
Temporal Resolution: 1 hour
Attributes: 2m temperature (K -> °C), 2m dewpoint temperature (K -> °C), 10m u/v wind components (m/s).
Note: ERA5-Land is a global gridded reanalysis model with a 2-3 month latency for consolidated data.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import math
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.providers.weather.base import BaseWeatherProvider, WeatherObservationDTO
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy

def kelvin_to_celsius(k: float) -> float:
    return round(k - 273.15, 2)

def calculate_rh_from_dewpoint(temp_c: float, dewpoint_c: float) -> Optional[float]:
    """Computes relative humidity from dry bulb and dewpoint temperature using Magnus-Tetens approximation."""
    try:
        a = 17.27
        b = 237.7
        alpha = ((a * temp_c) / (b + temp_c))
        beta = ((a * dewpoint_c) / (b + dewpoint_c))
        rh = 100.0 * math.exp(beta - alpha)
        return max(0.0, min(100.0, round(rh, 1)))
    except Exception:
        return None

class ERA5LandProvider(BaseWeatherProvider):
    def __init__(self):
        self.api_key = settings.CDS_API_KEY
        self.api_url = settings.CDS_API_URL or "https://cds.climate.copernicus.eu/api/v2"
        self.spatial_resolution_km = 9.0
        self.timeout = 10.0

    @property
    def provider_name(self) -> str:
        return "ERA5_LAND"

    async def get_current_observation(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherObservationDTO]:
        """
        ERA5-Land is an archived historical reanalysis dataset with 2-3 months latency.
        Real-time instantaneous observation is not supported by design; returns None.
        """
        return None

    async def get_observations_for_interval(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> List[WeatherObservationDTO]:
        """
        Retrieves historical gridded climate reanalysis from Copernicus CDS ERA5-Land.
        Queries the dataset 'reanalysis-era5-land' for the bounding box and time slice.
        """
        if not self.api_key:
            logger.info("Copernicus CDS API key not configured; skipping ERA5-Land historical fetch.")
            return []

        # CDS API retrieval payload
        request_payload = {
            "dataset": "reanalysis-era5-land",
            "variable": [
                "2m_temperature",
                "2m_dewpoint_temperature",
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
            ],
            "year": [str(start_time.year)],
            "month": [f"{start_time.month:02d}"],
            "day": [f"{start_time.day:02d}"],
            "time": [f"{h:02d}:00" for h in range(start_time.hour, min(24, end_time.hour + 1))],
            "area": [
                latitude + 0.1,  # North
                longitude - 0.1, # West
                latitude - 0.1,  # South
                longitude + 0.1, # East
            ],
            "format": "json",
        }

        headers = {
            "PRIVATE-TOKEN": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_url.rstrip('/')}/resources/reanalysis-era5-land",
                    json=request_payload,
                    headers=headers,
                )
                
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    return self.parse_era5_response(data, latitude, longitude, start_time)
                elif resp.status_code == 202:
                    # Async task queued in CDS processing queue; poll with backoff
                    job_data = resp.json()
                    request_id = job_data.get("request_id") or job_data.get("id")
                    status_url = resp.headers.get("Location") or f"{self.api_url.rstrip('/')}/tasks/{request_id}"
                    
                    import asyncio
                    for _ in range(3):
                        await asyncio.sleep(1.5)
                        poll_resp = await client.get(status_url, headers=headers)
                        if poll_resp.status_code == 200:
                            pdata = poll_resp.json()
                            state = (pdata.get("state") or pdata.get("status") or "").lower()
                            if state in ["completed", "successful", "complete"]:
                                result_url = pdata.get("location") or pdata.get("download_url")
                                if result_url:
                                    res_resp = await client.get(result_url, headers=headers)
                                    if res_resp.status_code == 200:
                                        return self.parse_era5_response(res_resp.json(), latitude, longitude, start_time)
                                return self.parse_era5_response(pdata, latitude, longitude, start_time)
                            elif state in ["failed", "aborted"]:
                                logger.warning(f"ERA5 CDS task failed: {pdata.get('error')}")
                                return []
                    return []
                else:
                    logger.warning(f"ERA5 CDS API returned HTTP {resp.status_code}: {resp.text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch ERA5-Land data from Copernicus CDS: {str(e)}")
            return []

    def parse_era5_response(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        base_time: datetime,
    ) -> List[WeatherObservationDTO]:
        """Parses structured CDS ERA5-Land time series into WeatherObservationDTO objects."""
        results: List[WeatherObservationDTO] = []
        series = data.get("series", data.get("values", []))
        
        for item in series:
            obs_dt = base_time
            if "time" in item:
                try:
                    obs_dt = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
                except Exception:
                    pass

            raw_temp = item.get("2m_temperature") if "2m_temperature" in item else item.get("t2m")
            raw_dew = item.get("2m_dewpoint_temperature") if "2m_dewpoint_temperature" in item else item.get("d2m")
            if raw_temp is None or raw_dew is None:
                logger.warning("ERA5-Land reanalysis record missing temperature or dewpoint; skipping invalid record.")
                continue

            temp_k = float(raw_temp)
            dew_k = float(raw_dew)
            
            temp_c = kelvin_to_celsius(temp_k)
            dew_c = kelvin_to_celsius(dew_k)
            rh_pct = calculate_rh_from_dewpoint(temp_c, dew_c)
            if rh_pct is None:
                logger.warning("ERA5 relative humidity could not be computed from dewpoint; skipping invalid record.")
                continue

            u_wind = float(item.get("10m_u_component_of_wind", item.get("u10", 0.0)))
            v_wind = float(item.get("10m_v_component_of_wind", item.get("v10", 0.0)))
            wind_speed = round(math.sqrt(u_wind ** 2 + v_wind ** 2), 1)

            hi_c, _ = calculate_heat_index(temp_c, rh_pct)
            wbgt_c = calculate_simplified_wbgt_proxy(temp_c, rh_pct, wind_speed_mps=wind_speed)

            results.append(
                WeatherObservationDTO(
                    provider_name=self.provider_name,
                    source_identifier=f"ERA5_LAND_GRID_{latitude:.2f}_{longitude:.2f} (Gridded Reanalysis 0.1°)",
                    data_type="GRIDDED_REANALYSIS",
                    latitude=latitude,
                    longitude=longitude,
                    spatial_resolution_km=self.spatial_resolution_km,
                    observed_at=obs_dt,
                    temperature_celsius=temp_c,
                    relative_humidity_pct=rh_pct,
                    heat_index_celsius=hi_c,
                    wbgt_estimated_celsius=wbgt_c,
                    wind_speed_mps=wind_speed,
                    solar_radiation_wm2=None,
                    confidence_score=0.85, # Gridded model, not direct station sensor
                    data_freshness_status="ARCHIVED_REANALYSIS",
                    validation_status="VALIDATED",
                    raw_payload=item,
                )
            )
        return results

    async def check_health(self) -> Dict[str, Any]:
        """CLIM-01: Verifies actual connectivity and authentication against Copernicus CDS API."""
        if not self.api_key:
            return {
                "provider": self.provider_name,
                "configured": False,
                "status": "UNCONFIGURED",
                "spatial_resolution_km": self.spatial_resolution_km,
                "temporal_resolution": "1 hour",
                "latency": "Reanalysis archive (2-3 months latency)",
                "disclaimer": "Copernicus ERA5-Land gridded reanalysis. API key required for historical queries.",
            }

        headers = {
            "PRIVATE-TOKEN": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(self.api_url.rstrip("/"), headers=headers)
                # If API endpoint responds with success or valid auth status
                is_operational = resp.status_code in [200, 204, 301, 302]
                status_str = "OPERATIONAL" if is_operational else f"DEGRADED_HTTP_{resp.status_code}"
                return {
                    "provider": self.provider_name,
                    "configured": True,
                    "status": status_str,
                    "spatial_resolution_km": self.spatial_resolution_km,
                    "temporal_resolution": "1 hour",
                    "latency": "2-3 months operational reanalysis lag",
                    "disclaimer": "Copernicus ERA5-Land 9km reanalysis model.",
                }
        except Exception as e:
            return {
                "provider": self.provider_name,
                "configured": True,
                "status": "UNREACHABLE",
                "error": str(e),
                "spatial_resolution_km": self.spatial_resolution_km,
                "temporal_resolution": "1 hour",
            }
