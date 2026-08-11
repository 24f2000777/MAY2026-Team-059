// Reverse geocoding via Nominatim (OpenStreetMap), shared by
// SubmitComplaint.vue's map picker and Nagrik Saathi's "share location"
// button - turns a GPS pin into a clean, human-readable address so
// neither has to trust a citizen typing something as vague as "Dharavi
// sector 5". Returns null on any failure, callers keep the raw
// coordinates either way and fall back to their own text-based flow.
export async function reverseGeocode(lat, lng) {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`
    )

    if (!response.ok) return null

    const data = await response.json()
    return data.display_name || null
  } catch {
    return null
  }
}
