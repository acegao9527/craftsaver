import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api/request'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('admin_token') || '')
  const userInfo = ref({
    username: 'Admin',
    avatar: ''
  })

  async function login(username, password) {
    const data = await request.post('/auth/login', { username, password })
    token.value = data.token
    localStorage.setItem('admin_token', data.token)
    return data
  }

  function logout() {
    token.value = ''
    userInfo.value = { username: '', avatar: '' }
    localStorage.removeItem('admin_token')
  }

  return {
    token,
    userInfo,
    login,
    logout
  }
})
