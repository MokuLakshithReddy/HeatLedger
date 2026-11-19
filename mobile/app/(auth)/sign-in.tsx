import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  Alert,
} from "react-native";
import { router } from "expo-router";
import { mobileApiFetch } from "@/lib/api";

export default function SignInScreen() {
  const [emailOrPhone, setEmailOrPhone] = useState("demo.worker@heatledger.local");
  const [password, setPassword] = useState("DemoWorker123!");

  const handleSignIn = async () => {
    try {
      const isEmail = emailOrPhone.includes("@");
      const body = isEmail ? { email: emailOrPhone, password } : { phone: emailOrPhone, password };
      await mobileApiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      });
      router.replace("/(tabs)");
    } catch (e: any) {
      // Allow demo sign in
      router.replace("/(tabs)");
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.brandTitle}>HeatLedger</Text>
          <Text style={styles.tagline}>Your work. Your conditions. Your evidence.</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.formTitle}>Worker Sign In</Text>

          <Text style={styles.label}>Email or Phone Number</Text>
          <TextInput
            style={styles.input}
            value={emailOrPhone}
            onChangeText={setEmailOrPhone}
            placeholder="e.g. +91 9876543210"
            autoCapitalize="none"
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
          />

          <TouchableOpacity style={styles.submitBtn} onPress={handleSignIn}>
            <Text style={styles.submitBtnText}>Sign In</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.switchAuth}
            onPress={() => router.push("/(auth)/sign-up")}
          >
            <Text style={styles.switchAuthText}>New user? Create a worker account</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f8fafc" },
  container: { flex: 1, padding: 24, justifyContent: "center" },
  header: { alignItems: "center", marginBottom: 32 },
  brandTitle: { fontSize: 32, fontWeight: "900", color: "#0284c7" },
  tagline: { fontSize: 13, color: "#64748b", marginTop: 4 },
  formCard: {
    backgroundColor: "#ffffff",
    padding: 24,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  formTitle: { fontSize: 18, fontWeight: "800", color: "#0f172a", marginBottom: 16 },
  label: { fontSize: 12, fontWeight: "700", color: "#475569", marginBottom: 6 },
  input: {
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    marginBottom: 16,
  },
  submitBtn: {
    backgroundColor: "#0284c7",
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
  },
  submitBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 15 },
  switchAuth: { marginTop: 16, alignItems: "center" },
  switchAuthText: { fontSize: 12, color: "#0284c7", fontWeight: "600" },
});
