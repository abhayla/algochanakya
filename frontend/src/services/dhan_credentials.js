/**
 * Dhan Credentials Service
 *
 * API calls for Dhan static token credential management (Tier 3).
 */
import api from './api'

export async function getCredentials() {
  const response = await api.get('/api/dhan-credentials/credentials')
  return response.data
}

export async function storeCredentials(credentials) {
  const response = await api.post('/api/dhan-credentials/credentials', credentials)
  return response.data
}

export async function deleteCredentials() {
  const response = await api.delete('/api/dhan-credentials/credentials')
  return response.data
}

export default { getCredentials, storeCredentials, deleteCredentials }
