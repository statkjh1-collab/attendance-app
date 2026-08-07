import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
})

export default api

export const EmployeesAPI = {
  list: (isActive) =>
    api.get('/employees', { params: isActive === undefined ? {} : { is_active: isActive } }).then((r) => r.data),
  create: (payload) => api.post('/employees', payload).then((r) => r.data),
  update: (id, payload) => api.put(`/employees/${id}`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/employees/${id}`).then((r) => r.data),
}

export const AttendanceAPI = {
  list: (params) => api.get('/attendance', { params }).then((r) => r.data),
  save: (payload) => api.post('/attendance', payload).then((r) => r.data),
  update: (id, payload) => api.put(`/attendance/${id}`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/attendance/${id}`).then((r) => r.data),
}

export const PayrollAPI = {
  get: (month) => api.get('/payroll', { params: { month } }).then((r) => r.data),
}
