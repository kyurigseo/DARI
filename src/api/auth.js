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
  // FormData(이미지 포함)인 경우 Content-Type을 직접 지정하지 않는다.
  // 직접 'multipart/form-data'를 세팅하면 boundary가 빠져 백엔드 파싱이 깨질 수 있으므로,
  // axios/브라우저가 boundary를 포함해 자동으로 채우도록 둔다.
  const { data } = await apiClient.patch('/auth/mypage/', payload)
  return data
}

export async function updateSettings(payload) {
  const { data } = await apiClient.patch('/auth/mypage/settings/', payload)
  return data
}

export function isAuthenticated() {
  return Boolean(tokenStorage.getAccess())
}
