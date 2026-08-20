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
  // apiClient 인스턴스는 기본 Content-Type이 'application/json'으로 고정돼 있다.
  // FormData를 보낼 때 이 기본값을 그대로 두면 axios의 기본 transformRequest가
  // "Content-Type이 이미 application/json이니 JSON으로 변환해야 한다"고 판단해서
  // FormData(이미지 포함)를 JSON 문자열로 바꿔버리고 실제 파일이 통째로 날아간다.
  // 요청 단위로 Content-Type을 명시적으로 비워서(undefined) 이 동작을 막고,
  // 브라우저가 boundary를 포함한 multipart/form-data 헤더를 직접 채우도록 한다.
  const { data } = await apiClient.patch('/auth/mypage/', payload, {
    headers: isFormData ? { 'Content-Type': undefined } : undefined,
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