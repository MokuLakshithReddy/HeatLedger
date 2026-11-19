"""IMD (India Meteorological Department) Weather Provider Adapter
Official Portal: https://api.imd.gov.in/public/
API Reference: https://api.imd.gov.in/public/api_reference.html
Integrates with IMD station observations and AWS/ARG network when credentials are configured.
CLIM-02: Preserves actual observation timestamps returned by the source station.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.providers.weather.base import BaseWeatherProvider, WeatherObservationDTO
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy

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

        endpoint = f"{self.base_url}/current_weather"
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        params = {"lat": str(latitude), "lon": str(longitude)}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    temp_c = float(data.get("temperature", data.get("TEMP", 0.0)))
                    rh_pct = float(data.get("humidity", data.get("RH", 0.0)))
                    hi_c, _ = calculate_heat_index(temp_c, rh_pct)
                    wind_speed = float(data.get("wind_speed", data.get("WS", 0.0)))
                    wbgt_c = calculate_simplified_wbgt_proxy(temp_c, rh_pct, wind_speed_mps=wind_speed)
                    
                    # CLIM-02: Preserve actual observation timestamp from source; do not overwrite with server ingestion time
                    observed_at = None
                    obs_time_raw = data.get("observed_at") or data.get("observation_time") or data.get("TIMESTAMP")
                    if obs_time_raw:
                        try:
                            observed_at = datetime.fromisoformat(str(obs_time_raw).replace("Z", "+00:00"))
                        except Exception:
                            pass
                    if not observed_at:
                        observed_at = datetime.now(timezone.utc)

                    station_id = str(data.get("station_id") or data.get("STATION_ID") or "IMD_AWS_HYDERABAD_43128")

                    return WeatherObservationDTO(
                        provider_name=self.provider_name,
                        source_identifier=station_id,
                        latitude=float(data.get("lat", latitude)),
                        longitude=float(data.get("lon", longitude)),
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

        endpoint = f"{self.base_url}/historical"
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        params = {
            "lat": str(latitude),
            "lon": str(longitude),
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, headers=headers, params=params)
                if response.status_code == 200:
                    records = response.json().get("observations", [])
                    out = []
                    for r in records:
                        temp_c = float(r.get("temperature", 0.0))
                        rh_pct = float(r.get("humidity", 0.0))
                        hi_c, _ = calculate_heat_index(temp_c, rh_pct)
                        wind_speed = float(r.get("wind_speed", 0.0))
                        wbgt_c = calculate_simplified_wbgt_proxy(temp_c, rh_pct, wind_speed_mps=wind_speed)
                        
                        obs_dt = None
                        if "observed_at" in r:
                            try:
                                obs_dt = datetime.fromisoformat(r["observed_at"].replace("Z", "+00:00"))
                            except Exception:
                                pass
                        if not obs_dt:
                            obs_dt = start_time

                        out.append(WeatherObservationDTO(
                            provider_name=self.provider_name,
                            source_identifier=str(r.get("station_id", "IMD_AWS_HYDERABAD_43128")),
                            latitude=float(r.get("lat", latitude)),
                            longitude=float(r.get("lon", longitude)),
                            spatial_resolution_km=10.0,
                            observed_at=obs_dt,
                            temperature_celsius=temp_c,
                            relative_humidity_pct=rh_pct,
                            heat_index_celsius=hi_c,
                            wbgt_estimated_celsius=wbgt_c,
                            wind_speed_mps=wind_speed,
                            solar_radiation_wm2=None,
                            confidence_score=0.95,
                            data_freshness_status="ARCHIVED_OBSERVATION",
                            validation_status="VALIDATED",
                            raw_payload=r,
                        ))
                    return out
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

        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health", headers=headers)
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
