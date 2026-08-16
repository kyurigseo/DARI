import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const ACCESS_TOKEN_KEY = 'dari_access_token'
const REFRESH_TOKEN_KEY = 'dari_refresh_token'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: ({ access, refresh }) => {
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// meetings 앱은 /api/meetings/ 프리픽스를 따로 씀 (accounts.urls가 두 경로에 중복 마운트됨)
export const meetingsClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
})

function attachAuthHeader(config) {
  const token = tokenStorage.getAccess()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

apiClient.interceptors.request.use(attachAuthHeader)
meetingsClient.interceptors.request.use(attachAuthHeader)

let refreshPromise = null

async function refreshAccessToken() {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) throw new Error('No refresh token')

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_BASE_URL}/api/v1/auth/refresh/`, { refresh })
      .then((res) => {
        tokenStorage.setTokens({ access: res.data.access })
        return res.data.access
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

function attachResponseInterceptor(instance) {
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config
      const status = error.response?.status

      if (status === 401 && !originalRequest._retry && tokenStorage.getRefresh()) {
        originalRequest._retry = true
        try {
          const newAccess = await refreshAccessToken()
          originalRequest.headers.Authorization = `Bearer ${newAccess}`
          return instance(originalRequest)
        } catch (refreshError) {
          tokenStorage.clear()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      }

      return Promise.reject(error)
    }
  )
}

attachResponseInterceptor(apiClient)
attachResponseInterceptor(meetingsClient)

export default apiClient
