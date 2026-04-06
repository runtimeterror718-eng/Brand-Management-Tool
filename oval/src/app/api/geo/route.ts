import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || "";
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY || process.env.SUPABASE_SERVICE_KEY || "";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const brandId = searchParams.get("brand_id");

  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.json({ error: "Supabase not configured", data: [] }, { status: 200 });
  }

  const supabase = createClient(supabaseUrl, supabaseKey);

  if (brandId) {
    // Fetch geo aggregates for a specific brand
    const { data, error } = await supabase
      .from("geo_aggregates")
      .select("*")
      .eq("brand_id", brandId)
      .order("negative_pct", { ascending: false });

    if (error) {
      return NextResponse.json({ error: error.message, data: [] }, { status: 200 });
    }

    return NextResponse.json({ data: data || [] });
  }

  // Fetch all brands, return geo for the first one
  const { data: brands } = await supabase.from("brands").select("id, name").limit(1);
  if (!brands || brands.length === 0) {
    return NextResponse.json({ data: [], message: "No brands found" });
  }

  const { data, error } = await supabase
    .from("geo_aggregates")
    .select("*")
    .eq("brand_id", brands[0].id)
    .order("negative_pct", { ascending: false });

  return NextResponse.json({
    brand: brands[0],
    data: data || [],
    error: error?.message,
  });
}
