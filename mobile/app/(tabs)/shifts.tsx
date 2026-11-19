import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  TextInput,
  Alert,
} from "react-native";
import { mobileApiFetch } from "@/lib/api";

const BREAK_TYPES = ["REST", "HYDRATION", "MEAL", "SHELTER"];

export default function ShiftsScreen() {
  const [shifts, setShifts] = useState<any[]>([]);
  const [activeShift, setActiveShift] = useState<any>(null);
  const [selectedBreakType, setSelectedBreakType] = useState("HYDRATION");
  const [breakNotes, setBreakNotes] = useState("");
  const [activeBreak, setActiveBreak] = useState<any>(null);

  useEffect(() => {
    loadShifts();
  }, []);

  async function loadShifts() {
    try {
      const summary = await mobileApiFetch<any>("/shifts/active");
      if (summary) setActiveShift(summary.active_shift);
      const list = await mobileApiFetch<any[]>("/shifts?limit=20");
      if (list) setShifts(list);
    } catch (e: any) {
      console.warn("Could not load shifts:", e);
      setShifts([]);
    }
  }

  const handleStartBreak = async () => {
    if (!activeShift) {
      Alert.alert("No Active Shift", "Start a shift first before recording a break.");
      return;
    }
    try {
      const b = await mobileApiFetch<any>(`/shifts/${activeShift.id}/breaks`, {
        method: "POST",
        body: JSON.stringify({ break_type: selectedBreakType, worker_notes: breakNotes }),
      });
      setActiveBreak(b);
      setBreakNotes("");
      Alert.alert("Break Recorded", `${selectedBreakType} break started.`);
      loadShifts();
    } catch (err: any) {
      Alert.alert("Break Error", err.message);
    }
  };

  const handleEndBreak = async () => {
    if (!activeBreak) return;
    try {
      await mobileApiFetch<any>(`/breaks/${activeBreak.id}/end`, { method: "POST" });
      setActiveBreak(null);
      Alert.alert("Break Ended", "Shift resumed to active.");
      loadShifts();
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Shift & Rest Management</Text>
        <Text style={styles.subtitle}>
          Record your rest periods. Missing GPS will never be treated as an unverified break.
        </Text>

        {/* Break Recording Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Declare Rest / Hydration Break</Text>
          <View style={styles.breakTypeRow}>
            {BREAK_TYPES.map((type) => (
              <TouchableOpacity
                key={type}
                style={[
                  styles.breakTypeBtn,
                  selectedBreakType === type && styles.breakTypeBtnActive,
                ]}
                onPress={() => setSelectedBreakType(type)}
              >
                <Text
                  style={[
                    styles.breakTypeText,
                    selectedBreakType === type && styles.breakTypeTextActive,
                  ]}
                >
                  {type}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <TextInput
            style={styles.notesInput}
            placeholder="Optional rest notes (e.g. shaded bus stop, dizzy from heat)..."
            value={breakNotes}
            onChangeText={setBreakNotes}
            multiline
          />

          {activeBreak ? (
            <TouchableOpacity style={styles.endBreakBtn} onPress={handleEndBreak}>
              <Text style={styles.btnText}>Conclude Break ({activeBreak.break_type})</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.startBreakBtn} onPress={handleStartBreak}>
              <Text style={styles.btnText}>Take {selectedBreakType} Break</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Shift History */}
        <Text style={styles.sectionHeader}>Recorded Shift History</Text>
        <View style={styles.historyList}>
          {shifts.map((s) => (
            <View key={s.id} style={styles.shiftItem}>
              <View style={styles.shiftHeader}>
                <Text style={styles.shiftDate}>
                  {new Date(s.started_at).toLocaleDateString()}
                </Text>
                <Text
                  style={[
                    styles.shiftStatusTag,
                    s.status === "COMPLETED" ? styles.tagCompleted : styles.tagActive,
                  ]}
                >
                  {s.status}
                </Text>
              </View>
              <View style={styles.shiftStatsRow}>
                <Text style={styles.statText}>Working: {s.total_working_minutes} mins</Text>
                <Text style={styles.statText}>Breaks: {s.total_break_minutes} mins</Text>
                <Text style={styles.statText}>
                  GPS: {s.location_tracking_enabled ? "Consented" : "Off"}
                </Text>
              </View>
            </View>
          ))}
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
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginBottom: 20,
  },
  cardTitle: { fontSize: 14, fontWeight: "700", color: "#0f172a", marginBottom: 12 },
  breakTypeRow: { flexDirection: "row", gap: 8, marginBottom: 12 },
  breakTypeBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#f1f5f9",
    alignItems: "center",
  },
  breakTypeBtnActive: { backgroundColor: "#0284c7" },
  breakTypeText: { fontSize: 11, fontWeight: "700", color: "#475569" },
  breakTypeTextActive: { color: "#ffffff" },
  notesInput: {
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    minHeight: 50,
    marginBottom: 12,
  },
  startBreakBtn: {
    backgroundColor: "#f59e0b",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  endBreakBtn: {
    backgroundColor: "#059669",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  btnText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  sectionHeader: { fontSize: 16, fontWeight: "800", color: "#0f172a", marginBottom: 10 },
  historyList: { gap: 10 },
  shiftItem: {
    backgroundColor: "#ffffff",
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  shiftHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  shiftDate: { fontSize: 13, fontWeight: "700", color: "#0f172a" },
  shiftStatusTag: { fontSize: 10, fontWeight: "800", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  tagCompleted: { backgroundColor: "#e2e8f0", color: "#475569" },
  tagActive: { backgroundColor: "#dcfce7", color: "#166534" },
  shiftStatsRow: { flexDirection: "row", justifyContent: "space-between" },
  statText: { fontSize: 11, color: "#64748b" },
});
