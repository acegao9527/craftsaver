import request from './request'

export default {
  list(params) {
    return request.get('/birthday/list', { params })
  },
  add(data) {
    return request.post('/birthday', data)
  },
  update(id, data) {
    return request.put(`/birthday/${id}`, data)
  },
  delete(id) {
    return request.delete(`/birthday/${id}`)
  },
  getTodayBirthdays() {
    return request.get('/birthday/today')
  }
}
