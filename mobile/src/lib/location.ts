/**
 * Continuous Consensual Location Collection Service
 * Manages foreground and background active shift GPS sampling at documented intervals (60s).
 * Strictly ceases collection upon shift completion or consent revocation.
 */
import { Platform } from "react-native";
import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import * as SecureStore from "expo-secure-store";
import { mobileApiFetch } from "@/lib/api";

export const BACKGROUND_LOCATION_TASK = "HEATLEDGER_BACKGROUND_LOCATION_TASK";
const ACTIVE_SHIFT_STORE_KEY = "heatledger_active_shift_id";
const OFFLINE_QUEUE_KEY = "heatledger_offline_location_queue";

let locationSubscription: Location.LocationSubscription | null = null;
let currentActiveShiftId: string | null = null;
let lastSampleTimestamp = 0;

export interface LocationCoordinates {
  latitude: number;
  longitude: number;
  accuracyMeters: number;
  altitudeMeters?: number | null;
  speedMps?: number | null;
  recordedAt?: string | null;
}

interface QueuedLocationSample {
  shiftId: string;
  coords: LocationCoordinates;
  enqueuedAt: number;
}

async function getOfflineQueue(): Promise<QueuedLocationSample[]> {
  try {
    let json: string | null = null;
    if (Platform.OS === "web") {
      json = localStorage.getItem(OFFLINE_QUEUE_KEY);
    } else {
      json = await SecureStore.getItemAsync(OFFLINE_QUEUE_KEY);
    }
    if (json) {
      return JSON.parse(json);
    }
  } catch (e) {
    console.warn("Could not read offline location queue:", e);
  }
  return [];
}

async function saveOfflineQueue(queue: QueuedLocationSample[]): Promise<void> {
  try {
    const trimmed = queue.slice(-200);
    const json = JSON.stringify(trimmed);
    if (Platform.OS === "web") {
      localStorage.setItem(OFFLINE_QUEUE_KEY, json);
    } else {
      await SecureStore.setItemAsync(OFFLINE_QUEUE_KEY, json);
    }
  } catch (e) {
    console.warn("Could not save offline location queue:", e);
  }
}

async function enqueueOfflineLocation(shiftId: string, coords: LocationCoordinates): Promise<void> {
  const queue = await getOfflineQueue();
  queue.push({ shiftId, coords, enqueuedAt: Date.now() });
  await saveOfflineQueue(queue);
}

async function flushOfflineLocationQueue(): Promise<void> {
  const queue = await getOfflineQueue();
  if (queue.length === 0) return;

  const byShift: Record<string, QueuedLocationSample[]> = {};
  for (const item of queue) {
    if (!byShift[item.shiftId]) byShift[item.shiftId] = [];
    byShift[item.shiftId].push(item);
  }

  const remaining: QueuedLocationSample[] = [];

  for (const [shiftId, samples] of Object.entries(byShift)) {
    try {
      const batchPayload = {
        samples: samples.map((s) => ({
          latitude: s.coords.latitude,
          longitude: s.coords.longitude,
          accuracy_meters: s.coords.accuracyMeters,
          altitude_meters: s.coords.altitudeMeters || null,
          speed_mps: s.coords.speedMps || null,
          recorded_at: s.coords.recordedAt || new Date(s.enqueuedAt).toISOString(),
        })),
      };

      await mobileApiFetch(`/shifts/${shiftId}/location-samples/batch`, {
        method: "POST",
        body: JSON.stringify(batchPayload),
      });
    } catch (e: any) {
      if (
        e.message &&
        (e.message.includes("403") ||
          e.message.includes("revoked") ||
          e.message.includes("not active") ||
          e.message.includes("404"))
      ) {
        console.warn(`Discarding queued locations for shift ${shiftId}: ${e.message}`);
      } else {
        remaining.push(...samples);
      }
    }
  }

  await saveOfflineQueue(remaining);
}

async function persistActiveShiftId(shiftId: string | null): Promise<void> {
  currentActiveShiftId = shiftId;
  try {
    if (shiftId) {
      if (Platform.OS === "web") {
        localStorage.setItem(ACTIVE_SHIFT_STORE_KEY, shiftId);
      } else {
        await SecureStore.setItemAsync(ACTIVE_SHIFT_STORE_KEY, shiftId);
      }
    } else {
      if (Platform.OS === "web") {
        localStorage.removeItem(ACTIVE_SHIFT_STORE_KEY);
      } else {
        await SecureStore.deleteItemAsync(ACTIVE_SHIFT_STORE_KEY);
      }
    }
  } catch (e) {
    console.warn("Could not persist active shift ID:", e);
  }
}

async function getStoredActiveShiftId(): Promise<string | null> {
  if (currentActiveShiftId) return currentActiveShiftId;
  try {
    if (Platform.OS === "web") {
      currentActiveShiftId = localStorage.getItem(ACTIVE_SHIFT_STORE_KEY);
    } else {
      currentActiveShiftId = await SecureStore.getItemAsync(ACTIVE_SHIFT_STORE_KEY);
    }
  } catch (e) {
    console.warn("Could not load stored active shift ID:", e);
  }
  return currentActiveShiftId;
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
        const locations = (data as any).locations as any[];
        const shiftId = currentActiveShiftId || (await getStoredActiveShiftId());
        if (shiftId) {
          for (const loc of locations) {
            if (!loc || !loc.coords) continue;
            const sampleTime = loc.timestamp || Date.now();
            if (sampleTime - lastSampleTimestamp >= 45000 || lastSampleTimestamp === 0) {
              lastSampleTimestamp = sampleTime;
              await LocationTrackingService.recordSample(shiftId, {
                latitude: loc.coords.latitude,
                longitude: loc.coords.longitude,
                accuracyMeters: loc.coords.accuracy || 10.0,
                altitudeMeters: loc.coords.altitude,
                speedMps: loc.coords.speed,
                recordedAt: new Date(sampleTime).toISOString(),
              });
            }
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

      await persistActiveShiftId(shiftId);
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
          recorded_at: coords.recordedAt || null,
        }),
      });
      // Drain and flush pending queued items on successful connectivity
      await flushOfflineLocationQueue();
    } catch (e: any) {
      if (
        e.message &&
        (e.message.includes("403") ||
          e.message.includes("revoked") ||
          e.message.includes("not active") ||
          e.message.includes("Cannot record location"))
      ) {
        console.warn("LocationTrackingService: Consent revoked or shift inactive. Halting tracking.");
        await LocationTrackingService.stopTracking();
        await saveOfflineQueue([]);
      } else {
        // Enqueue to persistent offline queue for replay upon reconnection
        console.warn("LocationTrackingService: Network error recording sample. Enqueueing offline.");
        await enqueueOfflineLocation(shiftId, coords);
      }
    }
  },

  async flushOfflineQueue(): Promise<void> {
    await flushOfflineLocationQueue();
  },

  async getOfflineQueueCount(): Promise<number> {
    const queue = await getOfflineQueue();
    return queue.length;
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
    await persistActiveShiftId(null);
  },
};
