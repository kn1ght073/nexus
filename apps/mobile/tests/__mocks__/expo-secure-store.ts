const store: Record<string, string> = {};

export const AFTER_FIRST_UNLOCK = 'AFTER_FIRST_UNLOCK';

export async function setItemAsync(key: string, value: string): Promise<void> {
  store[key] = value;
}

export async function getItemAsync(key: string): Promise<string | null> {
  return store[key] || null;
}

export async function deleteItemAsync(key: string): Promise<void> {
  delete store[key];
}
