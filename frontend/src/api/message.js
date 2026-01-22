import request from './request'

export default {
  list(params) {
    return request.get('/message/list', { params })
  },
  detail(id) {
    return request.get(`/message/${id}`)
  },
  delete(id) {
    return request.delete(`/message/${id}`)
  },
  stats() {
    return request.get('/message/stats')
  }
}
