import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseKey)

// --- Query helpers ---

export async function getBrands() {
  const { data, error } = await supabase.from('brands').select('*')
  if (error) throw error
  return data
}

export async function getMentions(brandId, { platform, limit = 100 } = {}) {
  let query = supabase
    .from('mentions')
    .select('*')
    .eq('brand_id', brandId)
    .order('scraped_at', { ascending: false })
    .limit(limit)

  if (platform) query = query.eq('platform', platform)
  const { data, error } = await query
  if (error) throw error
  return data
}

export async function getSeverityScores(brandId, { level, limit = 200 } = {}) {
  let query = supabase
    .from('severity_scores')
    .select('*')
    .eq('brand_id', brandId)
    .order('computed_at', { ascending: false })
    .limit(limit)

  if (level) query = query.eq('severity_level', level)
  const { data, error } = await query
  if (error) throw error
  return data
}

export async function getLatestAnalysis(brandId) {
  const { data, error } = await supabase
    .from('analysis_runs')
    .select('*')
    .eq('brand_id', brandId)
    .order('ran_at', { ascending: false })
    .limit(1)

  if (error) throw error
  return data?.[0] || null
}
