import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 45_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API Error]:', err.response?.data || err.message)
    return Promise.reject(err)
  }
)
