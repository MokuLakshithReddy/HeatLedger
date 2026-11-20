import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { mobileApiFetch } from "@/lib/api";
import * as Location from "expo-location";

interface ExposureData {
  temp: number;
  humidity: number;
  heatIndex: number;
  swbgt: number;
  riskCategory: string;
  stationName: string;
  providerName: string;
  dataType: string;
  isDemo: boolean;
  resolution: string;
  freshness: string;
  validation: string;
  solar?: number;
  wind?: number;
  observedAt: string;
}

export default function ExposureScreen() {
  const [exposureData, setExposureData] = useState<ExposureData | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadClimate();
  }, []);

  async function loadClimate() {
    setLoading(true);
    setErrorMsg(null);
    try {
      let lat = 17.3850;
      let lon = 78.4867;
      let hasRealGps = false;
      try {
        const { status } = await Location.getForegroundPermissionsAsync();
        if (status === "granted") {
          const currentPos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          if (currentPos) {
            lat = currentPos.coords.latitude;
            lon = currentPos.coords.longitude;
            hasRealGps = true;
          }
        }
      } catch (locErr) {
        // Fall back to regional coordinates
      }

      const res = await mobileApiFetch<any>(`/climate/current?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}`);
      if (res && res.temperature_celsius !== undefined) {
        setExposureData({
          temp: res.temperature_c ?? res.temperature_celsius,
          humidity: res.relative_humidity_pct,
          heatIndex: res.heat_index_c ?? res.heat_index_celsius,
          swbgt: res.swbgt_proxy_c ?? res.wbgt_estimated_celsius,
          riskCategory: res.risk_category || "CAUTION",
          stationName: res.station_name || res.source_identifier || "Meteorological Station",
          providerName: res.provider_name || "UNKNOWN",
          dataType: res.data_type || (res.provider_name === "ERA5_LAND" ? "GRIDDED_REANALYSIS" : "DIRECT_STATION_OBSERVATION"),
          isDemo: Boolean(res.is_demo || res.provider_name?.startsWith("DEMO") || res.validation_status === "DEMO_FIXTURE"),
          resolution: res.spatial_resolution_km ? `${res.spatial_resolution_km} km Grid` : "10.0 km Station Radius",
          freshness: res.data_freshness_status || "LIVE",
          validation: res.validation_status || "UNVALIDATED",
          solar: res.solar_radiation_wm2 ?? undefined,
          wind: res.wind_speed_mps ?? undefined,
          observedAt: res.observed_at || new Date().toISOString(),
        });
      } else {
        setErrorMsg("Weather observation data unavailable for current coordinates.");
      }
    } catch (e: any) {
      setErrorMsg("Unable to retrieve meteorological observations from server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Environmental Heat Exposure</Text>
        <Text style={styles.subtitle}>
          Accredited meteorological indicators matched to worker locations.
        </Text>

        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#0284c7" />
            <Text style={styles.loadingText}>Fetching meteorological telemetry...</Text>
          </View>
        ) : errorMsg || !exposureData ? (
          <View style={styles.unavailableCard}>
            <Text style={styles.unavailableTitle}>⚠️ Live Weather Unavailable</Text>
            <Text style={styles.unavailableText}>
              {errorMsg || "No active meteorological observation could be retrieved."}
            </Text>
            <TouchableOpacity style={styles.retryBtn} onPress={loadClimate}>
              <Text style={styles.retryBtnText}>Retry Connection</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            {/* Status & Provenance Banner */}
            {exposureData.isDemo ? (
              <View style={[styles.alertBanner, styles.demoBanner]}>
                <Text style={styles.demoBannerTitle}>🧪 DEMO SIMULATION NOTICE</Text>
                <Text style={styles.demoBannerText}>
                  Displaying simulated Hyderabad meteorological fixtures. Real IMD API key not active. Never presented as certified legal evidence.
                </Text>
              </View>
            ) : (
              <View style={[
                styles.alertBanner,
                exposureData.riskCategory === "EXTREME_DANGER" || exposureData.riskCategory === "DANGER"
                  ? styles.dangerBanner
                  : styles.cautionBanner
              ]}>
                <Text style={styles.alertBannerTitle}>
                  {exposureData.riskCategory === "EXTREME_DANGER" ? "🚨 EXTREME HEAT HAZARD" : "⚠️ Severe Climate Stress"}
                </Text>
                <Text style={styles.alertBannerText}>
                  Heat Index is in the {exposureData.riskCategory.replace("_", " ")} zone ({exposureData.heatIndex}°C). High risk of heat exhaustion. Take regular shaded rest breaks.
                </Text>
              </View>
            )}

            {/* Calculated Stress Indicators */}
            <View style={styles.card}>
              <Text style={styles.cardHeader}>Calculated Heat Stress Indicators</Text>
              <View style={styles.metricsGrid}>
                <View style={styles.metricItem}>
                  <Text style={styles.metricLabel}>Rothfusz Heat Index</Text>
                  <Text style={styles.metricLarge}>{exposureData.heatIndex}°C</Text>
                  <Text style={styles.metricNote}>Apparent Temperature</Text>
                </View>

                <View style={styles.metricItem}>
                  <Text style={styles.metricLabel}>sWBGT Proxy</Text>
                  <Text style={styles.metricLarge}>{exposureData.swbgt}°C</Text>
                  <Text style={styles.metricNote}>Australian BOM Formula</Text>
                </View>
              </View>
            </View>

            {/* Observed Variables */}
            <View style={styles.card}>
              <Text style={styles.cardHeader}>Observed Environmental Variables</Text>

              <View style={styles.row}>
                <Text style={styles.rowLabel}>Ambient Dry-Bulb Temp</Text>
                <Text style={styles.rowVal}>{exposureData.temp}°C</Text>
              </View>
              <View style={styles.row}>
                <Text style={styles.rowLabel}>Relative Humidity</Text>
                <Text style={styles.rowVal}>{exposureData.humidity}%</Text>
              </View>
              {exposureData.wind !== undefined && (
                <View style={styles.row}>
                  <Text style={styles.rowLabel}>Wind Speed</Text>
                  <Text style={styles.rowVal}>{exposureData.wind} m/s</Text>
                </View>
              )}
              {exposureData.solar !== undefined && (
                <View style={styles.row}>
                  <Text style={styles.rowLabel}>Solar Irradiance</Text>
                  <Text style={styles.rowVal}>{exposureData.solar} W/m²</Text>
                </View>
              )}
            </View>

            {/* Scientific Provenance & Classification */}
            <View style={styles.provenanceCard}>
              <Text style={styles.provenanceTitle}>Scientific Provenance & Data Type</Text>
              <Text style={styles.provenanceText}>• Source Provider: {exposureData.providerName}</Text>
              <Text style={styles.provenanceText}>• Station / Grid: {exposureData.stationName}</Text>
              <Text style={styles.provenanceText}>
                • Observation Type: {
                  exposureData.dataType === "GRIDDED_REANALYSIS"
                    ? "Gridded Atmospheric Reanalysis (ERA5-Land)"
                    : exposureData.dataType === "DIRECT_STATION_OBSERVATION"
                    ? "Direct In-Situ Station Measurement (IMD)"
                    : "Simulated Model Fixture"
                }
              </Text>
              <Text style={styles.provenanceText}>• Spatial Resolution: {exposureData.resolution}</Text>
              <Text style={styles.provenanceText}>• Freshness Status: {exposureData.freshness}</Text>
              <Text style={styles.provenanceText}>• Validation Status: {exposureData.validation}</Text>
              <Text style={styles.provenanceFootnote}>
                Note: sWBGT is an empirical mathematical proxy (BOM formula). Measured WBGT requires physical black-globe sensor apparatus.
              </Text>
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f8fafc" },
  container: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: "900", color: "#0f172a" },
  subtitle: { fontSize: 13, color: "#64748b", marginTop: 4, marginBottom: 16 },
  loadingContainer: { padding: 40, alignItems: "center" },
  loadingText: { marginTop: 12, fontSize: 13, color: "#64748b" },
  unavailableCard: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    alignItems: "center",
    marginVertical: 20,
  },
  unavailableTitle: { fontSize: 16, fontWeight: "800", color: "#b45309", marginBottom: 8 },
  unavailableText: { fontSize: 13, color: "#64748b", textAlign: "center", marginBottom: 16 },
  retryBtn: { backgroundColor: "#0284c7", paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 },
  retryBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 13 },
  alertBanner: { padding: 14, borderRadius: 12, marginBottom: 16 },
  dangerBanner: { backgroundColor: "#fef2f2", borderWidth: 1, borderColor: "#fecaca" },
  cautionBanner: { backgroundColor: "#fffbeb", borderWidth: 1, borderColor: "#fde68a" },
  demoBanner: { backgroundColor: "#eff6ff", borderWidth: 1, borderColor: "#bfdbfe" },
  alertBannerTitle: { fontSize: 14, fontWeight: "800", color: "#991b1b" },
  alertBannerText: { fontSize: 12, color: "#7f1d1d", marginTop: 4 },
  demoBannerTitle: { fontSize: 14, fontWeight: "800", color: "#1e40af" },
  demoBannerText: { fontSize: 12, color: "#1e3a8a", marginTop: 4 },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginBottom: 16,
  },
  cardHeader: { fontSize: 14, fontWeight: "800", color: "#0f172a", marginBottom: 12 },
  metricsGrid: { flexDirection: "row", gap: 12 },
  metricItem: {
    flex: 1,
    backgroundColor: "#f8fafc",
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    alignItems: "center",
  },
  metricLabel: { fontSize: 11, fontWeight: "600", color: "#64748b" },
  metricLarge: { fontSize: 26, fontWeight: "900", color: "#ea580c", marginVertical: 4 },
  metricNote: { fontSize: 10, color: "#94a3b8" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#f1f5f9",
  },
  rowLabel: { fontSize: 13, color: "#475569" },
  rowVal: { fontSize: 13, fontWeight: "700", color: "#0f172a" },
  provenanceCard: {
    backgroundColor: "#f8fafc",
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  provenanceTitle: { fontSize: 12, fontWeight: "800", color: "#334155", marginBottom: 6 },
  provenanceText: { fontSize: 11, color: "#64748b", marginVertical: 2 },
  provenanceFootnote: { fontSize: 10, color: "#94a3b8", fontStyle: "italic", marginTop: 8 },
});
