import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

/**
 * Get the primary brand (the one with the most mentions).
 * Returns { id, name } or null.
 */
export async function getPrimaryBrand(): Promise<{ id: string; name: string } | null> {
  if (!url || !key) return null;
  const sb = createClient(url, key);

  // Get brand with name 'PhysicsWallah'
  const { data: brands } = await sb
    .from("brands")
    .select("id, name")
    .eq("name", "PhysicsWallah");

  if (!brands?.length) {
    // Last fallback: any brand
    const { data: any } = await sb.from("brands").select("id, name").limit(1);
    return any?.[0] || null;
  }

  // Pick the one with the most mentions
  let best = brands[0];
  let bestCount = 0;
  for (const b of brands) {
    const { count } = await sb.from("mentions").select("id", { count: "exact", head: true }).eq("brand_id", b.id);
    if ((count || 0) > bestCount) {
      bestCount = count || 0;
      best = b;
    }
  }

  return best;
}

export function getSupabase() {
  if (!url || !key) return null;
  return createClient(url, key);
}
