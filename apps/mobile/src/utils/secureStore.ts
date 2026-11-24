import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const MEMORY_FALLBACK: Record<string, string> = {};

export async function setSecureItem(key: string, value: string): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(`nexus_sec_${key}`, value);
      } else {
        MEMORY_FALLBACK[key] = value;
      }
      return;
    }
    await SecureStore.setItemAsync(key, value, {
      keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
    });
  } catch (error) {
    console.warn(`[SecureStore] Error writing key ${key}:`, error);
    MEMORY_FALLBACK[key] = value;
  }
}

export async function getSecureItem(key: string): Promise<string | null> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(`nexus_sec_${key}`);
      }
      return MEMORY_FALLBACK[key] || null;
    }
    return await SecureStore.getItemAsync(key);
  } catch (error) {
    console.warn(`[SecureStore] Error reading key ${key}:`, error);
    return MEMORY_FALLBACK[key] || null;
  }
}

export async function deleteSecureItem(key: string): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(`nexus_sec_${key}`);
      }
      delete MEMORY_FALLBACK[key];
      return;
    }
    await SecureStore.deleteItemAsync(key);
  } catch (error) {
    console.warn(`[SecureStore] Error deleting key ${key}:`, error);
    delete MEMORY_FALLBACK[key];
  }
}
