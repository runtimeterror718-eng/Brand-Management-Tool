/**
 * Simple in-memory API response cache.
 * Caches full API responses for a configurable TTL.
 * Avoids repeated Supabase + RAG calls on every page navigation.
 */

const cache = new Map<string, { data: any; expiry: number }>();

const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

export function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (entry.expiry < Date.now()) {
    cache.delete(key);
    return null;
  }
  return entry.data as T;
}

export function setCache(key: string, data: any, ttl: number = DEFAULT_TTL) {
  cache.set(key, { data, expiry: Date.now() + ttl });
}

export function invalidateCache(prefix?: string) {
  if (!prefix) {
    cache.clear();
    return;
  }
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) cache.delete(key);
  }
}
