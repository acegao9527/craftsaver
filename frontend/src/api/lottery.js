import request from './request-public'

export function joinLottery(data) {
  return request({
    url: '/lottery/join',
    method: 'post',
    data
  })
}
