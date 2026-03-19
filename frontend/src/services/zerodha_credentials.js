/**
 * Zerodha Credentials Service
 *
 * API calls for Zerodha Kite Connect app credential management (Tier 3).
 */
import api from './api'

export async function getCredentials() {
  const response = await api.get('/api/zerodha-credentials/credentials')
  return response.data
}

export async function storeCredentials(credentials) {
  const response = await api.post('/api/zerodha-credentials/credentials', credentials)
  return response.data
}

export async function deleteCredentials() {
  const response = await api.delete('/api/zerodha-credentials/credentials')
  return response.data
}

export default { getCredentials, storeCredentials, deleteCredentials }
