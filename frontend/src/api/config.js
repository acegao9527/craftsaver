import request from './request'

export default {
  list() {
    return request.get('/config/list')
  },
  get(key) {
    return request.get(`/config/${key}`)
  },
  set(key, value) {
    return request.put(`/config/${key}`, { value })
  },
  delete(key) {
    return request.delete(`/config/${key}`)
  },
  getAll() {
    return request.get('/config/all')
  }
}
