/**
 * Upstox Credentials Service
 *
 * API calls for Upstox API app credential management (Tier 3).
 */
import api from './api'

export async function getCredentials() {
  const response = await api.get('/api/upstox-credentials/credentials')
  return response.data
}

export async function storeCredentials(credentials) {
  const response = await api.post('/api/upstox-credentials/credentials', credentials)
  return response.data
}

export async function deleteCredentials() {
  const response = await api.delete('/api/upstox-credentials/credentials')
  return response.data
}

export default { getCredentials, storeCredentials, deleteCredentials }
