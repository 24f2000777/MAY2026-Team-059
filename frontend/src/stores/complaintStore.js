import { defineStore } from 'pinia'
import {
  assignComplaint, createComplaint, getComplaintById, getComplaints,
  getComplaintsForCitizen, getComplaintsForStaff, getStaffList, updateComplaintStatus
} from '../api/client'

export const useComplaintStore = defineStore('complaints', {
  state: () => ({
    complaints: getComplaints(),
    staffList: getStaffList()
  }),
  actions: {
    refresh() { this.complaints = getComplaints() },
    forCitizen(id) { return getComplaintsForCitizen(id) },
    forStaff(id) { return getComplaintsForStaff(id) },
    byId(id) { return getComplaintById(id) },
    submit(data) { const c = createComplaint(data); this.refresh(); return c },
    updateStatus(id, status, note) { const c = updateComplaintStatus(id, status, note); this.refresh(); return c },
    assign(id, staffId) { const c = assignComplaint(id, staffId); this.refresh(); return c }
  }
})