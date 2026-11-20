/**
 * Continuous Consensual Location Collection Service
 * Manages foreground and background active shift GPS sampling at documented intervals (60s).
 * Strictly ceases collection upon shift completion or consent revocation.
 */
import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import { mobileApiFetch } from "@/lib/api";

export const BACKGROUND_LOCATION_TASK = "HEATLEDGER_BACKGROUND_LOCATION_TASK";

let locationSubscription: Location.LocationSubscription | null = null;
let currentActiveShiftId: string | null = null;
let lastSampleTimestamp = 0;

export interface LocationCoordinates {
  latitude: number;
  longitude: number;
  accuracyMeters: number;
  altitudeMeters?: number | null;
  speedMps?: number | null;
}

// Register background location task
try {
  if (!TaskManager.isTaskDefined(BACKGROUND_LOCATION_TASK)) {
    TaskManager.defineTask(BACKGROUND_LOCATION_TASK, async ({ data, error }) => {
      if (error) {
        console.warn("Background location task error:", error);
        return;
      }
      if (data && (data as any).locations && (data as any).locations.length > 0) {
        const loc = (data as any).locations[0];
        const shiftId = currentActiveShiftId;
        if (shiftId) {
          const now = Date.now();
          if (now - lastSampleTimestamp >= 45000) {
            lastSampleTimestamp = now;
            await LocationTrackingService.recordSample(shiftId, {
              latitude: loc.coords.latitude,
              longitude: loc.coords.longitude,
              accuracyMeters: loc.coords.accuracy || 10.0,
              altitudeMeters: loc.coords.altitude,
              speedMps: loc.coords.speed,
            });
          }
        }
      }
    });
  }
} catch (e) {
  console.warn("Could not register background location task:", e);
}

export const LocationTrackingService = {
  isTrackingActive(): boolean {
    return locationSubscription !== null || currentActiveShiftId !== null;
  },

  getCurrentShiftId(): string | null {
    return currentActiveShiftId;
  },

  async startTrackingForShift(shiftId: string): Promise<boolean> {
    try {
      // 1. Check foreground permissions
      const { status: fgStatus } = await Location.requestForegroundPermissionsAsync();
      if (fgStatus !== "granted") {
        console.warn("LocationTrackingService: Foreground permission not granted.");
        return false;
      }

      // 2. Stop any existing tracking
      await LocationTrackingService.stopTracking();

      currentActiveShiftId = shiftId;
      lastSampleTimestamp = Date.now();

      // 3. Take initial position sample
      try {
        const initialFix = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        await LocationTrackingService.recordSample(shiftId, {
          latitude: initialFix.coords.latitude,
          longitude: initialFix.coords.longitude,
          accuracyMeters: initialFix.coords.accuracy || 10.0,
          altitudeMeters: initialFix.coords.altitude,
          speedMps: initialFix.coords.speed,
        });
      } catch (fixErr) {
        console.warn("LocationTrackingService: Initial GPS fix timeout:", fixErr);
      }

      // 4. Request background permission for continuous tracking
      try {
        const { status: bgStatus } = await Location.requestBackgroundPermissionsAsync();
        if (bgStatus === "granted" && TaskManager.isTaskDefined(BACKGROUND_LOCATION_TASK)) {
          await Location.startLocationUpdatesAsync(BACKGROUND_LOCATION_TASK, {
            accuracy: Location.Accuracy.Balanced,
            timeInterval: 60000, // 60 seconds
            distanceInterval: 50, // 50 meters
            deferredUpdatesInterval: 60000,
            showsBackgroundLocationIndicator: true,
            foregroundService: {
              notificationTitle: "HeatLedger Shift Active",
              notificationBody: "Monitoring environmental heat exposure during your shift.",
              notificationColor: "#0284c7",
            },
          });
        }
      } catch (bgErr) {
        console.warn("Background tracking not available, continuing with foreground watch:", bgErr);
      }

      // 5. Start periodic foreground watcher
      locationSubscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.Balanced,
          timeInterval: 60000, // 60 seconds
          distanceInterval: 50, // 50 meters
        },
        async (loc) => {
          if (!currentActiveShiftId) {
            await LocationTrackingService.stopTracking();
            return;
          }
          // Throttle to at most once per 45 seconds
          const now = Date.now();
          if (now - lastSampleTimestamp >= 45000) {
            lastSampleTimestamp = now;
            await LocationTrackingService.recordSample(currentActiveShiftId, {
              latitude: loc.coords.latitude,
              longitude: loc.coords.longitude,
              accuracyMeters: loc.coords.accuracy || 10.0,
              altitudeMeters: loc.coords.altitude,
              speedMps: loc.coords.speed,
            });
          }
        }
      );

      return true;
    } catch (err) {
      console.error("LocationTrackingService: Failed to start location tracking:", err);
      return false;
    }
  },

  async recordSample(shiftId: string, coords: LocationCoordinates): Promise<void> {
    try {
      await mobileApiFetch(`/shifts/${shiftId}/location-samples`, {
        method: "POST",
        body: JSON.stringify({
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy_meters: coords.accuracyMeters,
          altitude_meters: coords.altitudeMeters || null,
          speed_mps: coords.speedMps || null,
        }),
      });
    } catch (e: any) {
      if (e.message && (e.message.includes("403") || e.message.includes("revoked") || e.message.includes("not active"))) {
        console.warn("LocationTrackingService: Consent revoked or shift inactive. Halting tracking.");
        await LocationTrackingService.stopTracking();
      }
    }
  },

  async stopTracking(): Promise<void> {
    if (locationSubscription) {
      locationSubscription.remove();
      locationSubscription = null;
    }
    try {
      const hasBg = await Location.hasStartedLocationUpdatesAsync(BACKGROUND_LOCATION_TASK);
      if (hasBg) {
        await Location.stopLocationUpdatesAsync(BACKGROUND_LOCATION_TASK);
      }
    } catch (e) {
      // Background task not active
    }
    currentActiveShiftId = null;
  },
};
