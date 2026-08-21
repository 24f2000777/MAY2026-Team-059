// The backend assigns a short sequential complaint_number (see the
// add_complaint_number migration) alongside the real UUID id. The UUID
// stays the actual identifier for URLs/API calls, this is purely a
// human-friendly reference to show in the UI instead of the raw UUID.
export function complaintReference(complaintNumber) {
  return `NGK-${String(complaintNumber).padStart(6, '0')}`
}
