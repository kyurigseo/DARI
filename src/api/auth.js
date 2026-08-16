import apiClient, { tokenStorage } from './client'

export async function signup(payload) {
  const { data } = await apiClient.post('/auth/signup/', payload)
  return data
}

export async function login({ username, password }) {
  const { data } = await apiClient.post('/auth/login/', { username, password })
  tokenStorage.setTokens({ access: data.access, refresh: data.refresh })
  return data
}

export async function logout() {
  const refresh = tokenStorage.getRefresh()
  try {
    await apiClient.post('/auth/logout/', { refresh })
  } finally {
    tokenStorage.clear()
  }
}

export async function getMe() {
  const { data } = await apiClient.get('/auth/me/')
  return data
}

export async function getMyPage() {
  const { data } = await apiClient.get('/auth/mypage/')
  return data
}

export async function updateMyPage(payload) {
  const isFormData = typeof FormData !== 'undefined' && payload instanceof FormData
  const { data } = await apiClient.patch('/auth/mypage/', payload, {
    headers: isFormData ? { 'Content-Type': 'multipart/form-data' } : undefined,
  })
  return data
}

export async function updateSettings(payload) {
  const { data } = await apiClient.patch('/auth/mypage/settings/', payload)
  return data
}

export function isAuthenticated() {
  return Boolean(tokenStorage.getAccess())
}
