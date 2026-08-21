// Real ComplaintStatus enum values (Backend/app/schemas/complaint.py).
// Colors are literal hex, not CSS var(--...) references: DonutChart
// binds them as a raw SVG stroke attribute, and var() doesn't resolve
// there the way it does inside an actual style block. Values match
// this app's --warn/--accent/--ok/--danger/--text-dim design tokens.
const STATUS_LABELS = {
  submitted: 'Submitted',
  pending_approval: 'Pending Approval',
  approved: 'Approved',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn'
}

const STATUS_COLORS = {
  submitted: '#B8860B',
  pending_approval: '#B8860B',
  approved: '#2F8F5B',
  in_progress: '#2F8F5B',
  resolved: '#2A9D8F',
  closed: '#5E6B5A',
  rejected: '#C0392B',
  withdrawn: '#5E6B5A'
}

// Lifecycle order, not alphabetical or count-based, so the donut
// legend reads like a complaint's actual journey left to right.
const STATUS_ORDER = Object.keys(STATUS_LABELS)

export function statusLabel(value) {
  return STATUS_LABELS[value] || value
}

// Builds DonutChart's segments prop straight from an analytics
// endpoint's status_counts map, statuses with zero omitted so the
// legend doesn't pad itself out with a pile of zeros.
export function statusSegments(statusCounts) {
  return STATUS_ORDER.filter((s) => statusCounts[s] > 0).map((s) => ({
    label: STATUS_LABELS[s],
    value: statusCounts[s],
    color: STATUS_COLORS[s]
  }))
}

// "Done" bucket shared by every stat card that shows a resolved
// count: resolved and closed both count, same convention
// AdminDashboard.vue already uses for its own Resolved stat.
export function doneCount(statusCounts) {
  return (statusCounts.resolved || 0) + (statusCounts.closed || 0)
}

// Whatever's left once you take out done/rejected/withdrawn, still
// needs attention from someone.
export function openCount(total, statusCounts) {
  return total - doneCount(statusCounts) - (statusCounts.rejected || 0) - (statusCounts.withdrawn || 0)
}
