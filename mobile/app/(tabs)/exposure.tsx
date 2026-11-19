import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
} from "react-native";
import { mobileApiFetch } from "@/lib/api";

export default function ExposureScreen() {
  const [exposureData, setExposureData] = useState<any>({
    temp: 41.5,
    humidity: 38,
    heatIndex: 48.2,
    swbgt: 32.4,
    riskCategory: "EXTREME_DANGER",
    stationName: "Begumpet Observatory (IMD / AWS Grid)",
    resolution: "5.0 km Urban Grid",
    freshness: "DEMO_SAMPLE",
    validation: "FALLBACK",
    solar: 780,
    wind: 3.8,
  });

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Environmental Heat Exposure</Text>
        <Text style={styles.subtitle}>
          Accredited meteorological indicators matched to your working shifts.
        </Text>

        {/* Big Alert Banner */}
        <View style={styles.alertBanner}>
          <Text style={styles.alertBannerTitle}>⚠️ Severe Climate Stress Detected</Text>
          <Text style={styles.alertBannerText}>
            Heat Index is in the {exposureData.riskCategory.replace("_", " ")} zone. Increased risk of heat exhaustion and cramps. Hydrate frequently.
          </Text>
        </View>

        {/* Primary Indicator Cards */}
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
              <Text style={styles.metricNote}>Estimated Wet-Bulb</Text>
            </View>
          </View>
        </View>

        {/* Meteorological Observations */}
        <View style={styles.card}>
          <Text style={styles.cardHeader}>Observed Weather Variables</Text>

          <View style={styles.row}>
            <Text style={styles.rowLabel}>Ambient Temperature</Text>
            <Text style={styles.rowVal}>{exposureData.temp}°C</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Relative Humidity</Text>
            <Text style={styles.rowVal}>{exposureData.humidity}%</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Wind Speed</Text>
            <Text style={styles.rowVal}>{exposureData.wind} m/s</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Solar Irradiance</Text>
            <Text style={styles.rowVal}>{exposureData.solar} W/m²</Text>
          </View>
        </View>

        {/* Attribution & Provenance Card */}
        <View style={styles.provenanceCard}>
          <Text style={styles.provenanceTitle}>Scientific Provenance & Transparency</Text>
          <Text style={styles.provenanceText}>• Source: {exposureData.stationName}</Text>
          <Text style={styles.provenanceText}>• Spatial Resolution: {exposureData.resolution}</Text>
          <Text style={styles.provenanceText}>• Data Freshness Status: {exposureData.freshness}</Text>
          <Text style={styles.provenanceText}>• Validation Mode: {exposureData.validation}</Text>
          <Text style={styles.provenanceFootnote}>
            Note: sWBGT is an empirical mathematical proxy (BOM formula). Measured WBGT requires direct black-globe sensor equipment.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f8fafc" },
  container: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: "900", color: "#0f172a" },
  subtitle: { fontSize: 13, color: "#64748b", marginTop: 4, marginBottom: 16 },
  alertBanner: {
    backgroundColor: "#fef2f2",
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#fecaca",
    marginBottom: 16,
  },
  alertBannerTitle: { fontSize: 14, fontWeight: "800", color: "#b91c1c", marginBottom: 2 },
  alertBannerText: { fontSize: 12, color: "#991b1b", lineHeight: 17 },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginBottom: 16,
  },
  cardHeader: { fontSize: 14, fontWeight: "800", color: "#0f172a", marginBottom: 14 },
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
  metricLarge: { fontSize: 28, fontWeight: "900", color: "#ea580c", marginVertical: 4 },
  metricNote: { fontSize: 10, color: "#94a3b8" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#f1f5f9",
  },
  rowLabel: { fontSize: 13, color: "#64748b" },
  rowVal: { fontSize: 13, fontWeight: "700", color: "#0f172a" },
  provenanceCard: {
    backgroundColor: "#f1f5f9",
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  provenanceTitle: { fontSize: 12, fontWeight: "800", color: "#334155", marginBottom: 6 },
  provenanceText: { fontSize: 11, color: "#475569", marginBottom: 2 },
  provenanceFootnote: { fontSize: 10, color: "#64748b", fontStyle: "italic", marginTop: 6 },
});
