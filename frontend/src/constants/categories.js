// Real ComplaintCategory enum values (Backend/app/schemas/complaint.py),
// shared between SubmitComplaint.vue and CitizenDashboard.vue so the
// display labels can't drift between where a complaint is filed and
// where it's shown back.
export const CATEGORIES = [
  { value: 'pothole', label: 'Pothole' },
  { value: 'road', label: 'Road Damage' },
  { value: 'streetlight', label: 'Streetlight Outage' },
  { value: 'drainage', label: 'Drainage / Flooding' },
  { value: 'garbage', label: 'Garbage Collection' },
  { value: 'water_supply', label: 'Water Supply' },
  { value: 'sewage', label: 'Sewage' },
  { value: 'traffic', label: 'Traffic' },
  { value: 'electricity', label: 'Electricity' },
  { value: 'other', label: 'Other' }
]

export function categoryLabel(value) {
  return CATEGORIES.find(c => c.value === value)?.label || value
}

// Turns an analytics endpoint's category_counts map into
// [{ label, count }], sorted highest first, for the bar-chart style
// category breakdown the analytics pages share.
export function categoryBreakdown(categoryCounts) {
  return Object.entries(categoryCounts)
    .map(([value, count]) => ({ label: categoryLabel(value), count }))
    .sort((a, b) => b.count - a.count)
}
