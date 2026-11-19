import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  Alert,
} from "react-native";
import { router } from "expo-router";
import { Language, translations } from "@/lib/i18n";
import { SessionStore } from "@/lib/store";
import { mobileApiFetch } from "@/lib/api";
import * as Location from "expo-location";

export default function WorkerDashboard() {
  const [lang, setLang] = useState<Language>("te"); // Default Telugu for Hyderabad workers
  const t = translations[lang];
  const user = SessionStore.get();

  const [activeShift, setActiveShift] = useState<any>(null);
  const [todayWorkMins, setTodayWorkMins] = useState(0);
  const [todayBreakMins, setTodayBreakMins] = useState(0);
  const [weatherObs, setWeatherObs] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function init() {
      let current = SessionStore.get();
      if (!current) {
        current = await SessionStore.loadStoredSession();
      }
      if (!current) {
        router.replace("/(auth)/sign-in");
        return;
      }
      loadDashboard();
    }
    init();
  }, []);

  async function loadDashboard() {
    try {
      const data = await mobileApiFetch<any>("/shifts/active");
      if (data) {
        setActiveShift(data.active_shift);
        setTodayWorkMins(data.today_working_minutes || 0);
        setTodayBreakMins(data.today_break_minutes || 0);
      }
    } catch (err: any) {
      console.warn("Failed to load active shift", err);
    }

    try {
      const climate = await mobileApiFetch<any>("/climate/current?latitude=17.3850&longitude=78.4867");
      if (climate) {
        setWeatherObs({
          temp: climate.temperature_c,
          rh: climate.relative_humidity_pct,
          hi: climate.heat_index_c,
          wbgt: climate.swbgt_proxy_c,
          risk: climate.risk_category,
          station: climate.station_name || "Begumpet Observatory",
          freshness: climate.freshness_indicator || "ACCURATE",
        });
      }
    } catch (err: any) {
      console.warn("Failed to load live climate", err);
    }
  }

  const handleStartShift = async () => {
    setLoading(true);
    let trackingAllowed = false;
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      trackingAllowed = (status === "granted");
    } catch (permErr) {
      console.warn("Location permission request:", permErr);
    }

    try {
      const newShift = await mobileApiFetch<any>("/shifts/start", {
        method: "POST",
        body: JSON.stringify({ location_tracking_enabled: trackingAllowed }),
      });
      setActiveShift(newShift);

      if (trackingAllowed) {
        try {
          const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          await mobileApiFetch(`/shifts/${newShift.id}/location-samples`, {
            method: "POST",
            body: JSON.stringify({
              latitude: loc.coords.latitude,
              longitude: loc.coords.longitude,
              accuracy_meters: loc.coords.accuracy || 10.0,
            }),
          });
        } catch (locErr) {
          console.warn("Initial location sample fix error:", locErr);
        }
      }

      Alert.alert(
        "Shift Started",
        trackingAllowed
          ? "Your work and consensual GPS exposure are being recorded."
          : "Shift active without location tracking (permission off)."
      );
      loadDashboard();
    } catch (e: any) {
      Alert.alert("Shift Error", e.message || "Failed to start shift");
    } finally {
      setLoading(false);
    }
  };

  const handleEndShift = async () => {
    if (!activeShift) return;
    setLoading(true);
    try {
      await mobileApiFetch<any>(`/shifts/${activeShift.id}/end`, { method: "POST" });
      setActiveShift(null);
      Alert.alert("Shift Concluded", "Your working hours have been saved to your timeline.");
      loadDashboard();
    } catch (e: any) {
      Alert.alert("Error Ending Shift", e.message || "Failed to end shift");
    } finally {
      setLoading(false);
    }
  };

  const greeting = user?.fullName
    ? (lang === "te" ? `నమస్కారం, ${user.fullName} గారు` : (lang === "hi" ? `नमस्ते, ${user.fullName}` : `Welcome, ${user.fullName}`))
    : (lang === "te" ? "నమస్కారం కార్మికుడు" : "Welcome Worker");

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* Header Bar */}
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.appName}>{t.app_title}</Text>
            <Text style={styles.workerGreeting}>{greeting}</Text>
          </View>
          <View style={styles.langSelector}>
            {(["te", "hi", "en"] as Language[]).map((l) => (
              <TouchableOpacity
                key={l}
                onPress={() => setLang(l)}
                style={[styles.langBtn, lang === l && styles.langBtnActive]}
              >
                <Text style={[styles.langBtnText, lang === l && styles.langBtnTextActive]}>
                  {l.toUpperCase()}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Demo Mode & Jurisdiction Badge */}
        <View style={styles.jurisdictionCard}>
          <Text style={styles.jurisdictionText}>📍 {t.hyderabad_location} • తెలంగాణ (Telangana)</Text>
          <Text style={styles.demoBadge}>DEMO PILOT</Text>
        </View>

        {/* Big Action Card: Shift Status & Controls */}
        <View style={styles.shiftCard}>
          <View style={styles.shiftStatusRow}>
            <Text style={styles.cardLabel}>{t.active_shift}</Text>
            <View
              style={[
                styles.statusBadge,
                activeShift?.status === "ACTIVE"
                  ? styles.statusActive
                  : styles.statusInactive,
              ]}
            >
              <Text style={styles.statusBadgeText}>
                {activeShift ? activeShift.status : t.no_active_shift}
              </Text>
            </View>
          </View>

          {activeShift ? (
            <View style={styles.activeShiftContent}>
              <Text style={styles.shiftTimer}>
                {activeShift.status === "ACTIVE" ? "🟢 Shift in Progress" : "⏸️ On Break"}
              </Text>
              <Text style={styles.locationNotice}>
                {activeShift.location_tracking_enabled
                  ? "📍 " + t.location_on
                  : "🔒 " + t.location_off}
              </Text>

              <View style={styles.shiftActionRow}>
                <TouchableOpacity
                  style={[styles.actionBtn, styles.pauseBtn]}
                  onPress={() => router.push("/shifts")}
                >
                  <Text style={styles.actionBtnText}>{t.pause_shift}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionBtn, styles.endBtn]}
                  onPress={handleEndShift}
                >
                  <Text style={styles.actionBtnText}>{t.end_shift}</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.startShiftBigButton}
              onPress={handleStartShift}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.startShiftBtnText}>⚡ {t.start_shift}</Text>
              )}
            </TouchableOpacity>
          )}
        </View>

        {/* Today's Working & Break Metrics */}
        <View style={styles.metricsRow}>
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>{t.today_work}</Text>
            <Text style={styles.metricValue}>{Math.round(todayWorkMins / 60)} hrs</Text>
            <Text style={styles.metricSub}>{todayWorkMins} minutes</Text>
          </View>
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>{t.today_breaks}</Text>
            <Text style={styles.metricValue}>{todayBreakMins} min</Text>
            <Text style={styles.metricSub}>Worker Declared</Text>
          </View>
        </View>

        {/* Live Environmental Exposure Card */}
        {weatherObs ? (
          <View style={styles.heatCard}>
            <View style={styles.heatHeader}>
              <Text style={styles.heatTitle}>🔥 {t.live_heat_index}</Text>
              <Text style={styles.dangerTag}>{weatherObs.risk ? weatherObs.risk.replace("_", " ") : "CAUTION"}</Text>
            </View>

            <View style={styles.heatNumbersRow}>
              <View>
                <Text style={styles.heatBigNumber}>{weatherObs.hi}°C</Text>
                <Text style={styles.heatSubText}>Apparent Rothfusz HI</Text>
              </View>
              <View style={styles.heatDivider} />
              <View>
                <Text style={styles.heatSubNumber}>{weatherObs.temp}°C</Text>
                <Text style={styles.heatSubText}>Ambient Temp</Text>
              </View>
              <View style={styles.heatDivider} />
              <View>
                <Text style={styles.heatSubNumber}>{weatherObs.wbgt}°C</Text>
                <Text style={styles.heatSubText}>sWBGT Proxy</Text>
              </View>
            </View>

            <Text style={styles.heatStationFootnote}>
              Station: {weatherObs.station} • Relative Humidity: {weatherObs.rh}%
            </Text>
          </View>
        ) : (
          <View style={styles.heatCard}>
            <Text style={styles.heatTitle}>Weather Telemetry</Text>
            <Text style={styles.heatSubText}>Connecting to meteorological observation feed...</Text>
          </View>
        )}

        {/* Quick Access Buttons */}
        <View style={styles.quickActionsContainer}>
          <TouchableOpacity
            style={styles.quickActionBtn}
            onPress={() => router.push("/earnings")}
          >
            <Text style={styles.quickActionEmoji}>📄</Text>
            <Text style={styles.quickActionText}>{t.upload_earnings}</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.quickActionBtn}
            onPress={() => router.push("/reports")}
          >
            <Text style={styles.quickActionEmoji}>🛡️</Text>
            <Text style={styles.quickActionText}>{t.evidence_timeline}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f8fafc",
  },
  container: {
    padding: 16,
    paddingBottom: 40,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  appName: {
    fontSize: 22,
    fontWeight: "900",
    color: "#0284c7",
    letterSpacing: -0.5,
  },
  workerGreeting: {
    fontSize: 13,
    color: "#334155",
    fontWeight: "600",
    marginTop: 2,
  },
  langSelector: {
    flexDirection: "row",
    backgroundColor: "#e2e8f0",
    borderRadius: 8,
    padding: 2,
  },
  langBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  langBtnActive: {
    backgroundColor: "#ffffff",
  },
  langBtnText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#64748b",
  },
  langBtnTextActive: {
    color: "#0284c7",
  },
  jurisdictionCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fef3c7",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#fde68a",
  },
  jurisdictionText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#92400e",
  },
  demoBadge: {
    fontSize: 10,
    fontWeight: "800",
    color: "#b45309",
    backgroundColor: "#ffffff",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  shiftCard: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 18,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  shiftStatusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    color: "#64748b",
    letterSpacing: 0.5,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  statusActive: {
    backgroundColor: "#dcfce7",
  },
  statusInactive: {
    backgroundColor: "#f1f5f9",
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#166534",
  },
  startShiftBigButton: {
    backgroundColor: "#0284c7",
    paddingVertical: 18,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  startShiftBtnText: {
    color: "#ffffff",
    fontSize: 17,
    fontWeight: "800",
  },
  activeShiftContent: {
    alignItems: "center",
    paddingVertical: 6,
  },
  shiftTimer: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0f172a",
    marginBottom: 4,
  },
  locationNotice: {
    fontSize: 12,
    color: "#0369a1",
    fontWeight: "600",
    marginBottom: 14,
  },
  shiftActionRow: {
    flexDirection: "row",
    gap: 12,
    width: "100%",
  },
  actionBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  pauseBtn: {
    backgroundColor: "#f59e0b",
  },
  endBtn: {
    backgroundColor: "#dc2626",
  },
  actionBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 14,
  },
  metricsRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  metricCard: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  metricLabel: {
    fontSize: 11,
    color: "#64748b",
    fontWeight: "600",
  },
  metricValue: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0f172a",
    marginTop: 4,
  },
  metricSub: {
    fontSize: 10,
    color: "#94a3b8",
    marginTop: 2,
  },
  heatCard: {
    backgroundColor: "#fff7ed",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#ffedd5",
    marginBottom: 16,
  },
  heatHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  heatTitle: {
    fontSize: 13,
    fontWeight: "800",
    color: "#9a3412",
  },
  dangerTag: {
    backgroundColor: "#ea580c",
    color: "#ffffff",
    fontSize: 10,
    fontWeight: "800",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  heatNumbersRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    paddingVertical: 8,
  },
  heatBigNumber: {
    fontSize: 28,
    fontWeight: "900",
    color: "#c2410c",
  },
  heatSubNumber: {
    fontSize: 18,
    fontWeight: "700",
    color: "#475569",
  },
  heatDivider: {
    width: 1,
    height: 32,
    backgroundColor: "#fed7aa",
  },
  heatSubText: {
    fontSize: 10,
    color: "#7c2d12",
    marginTop: 2,
    fontWeight: "600",
  },
  heatStationFootnote: {
    fontSize: 10,
    color: "#9a3412",
    marginTop: 8,
    textAlign: "center",
  },
  quickActionsContainer: {
    flexDirection: "row",
    gap: 12,
  },
  quickActionBtn: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  quickActionEmoji: {
    fontSize: 24,
    marginBottom: 6,
  },
  quickActionText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#0f172a",
    textAlign: "center",
  },
});
