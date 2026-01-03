/**
 * SmartAPI Service
 *
 * API calls for SmartAPI credential management and configuration
 */
import api from './api'

/**
 * Get SmartAPI credentials status
 * @returns {Promise<Object>} Credentials status (does not return actual credentials)
 */
export async function getCredentials() {
  const response = await api.get('/api/smartapi/credentials')
  return response.data
}

/**
 * Store SmartAPI credentials
 * @param {Object} credentials - { client_id, pin, totp_secret }
 * @returns {Promise<Object>} Stored credentials status
 */
export async function storeCredentials(credentials) {
  const response = await api.post('/api/smartapi/credentials', credentials)
  return response.data
}

/**
 * Delete SmartAPI credentials
 * @returns {Promise<Object>} Success message
 */
export async function deleteCredentials() {
  const response = await api.delete('/api/smartapi/credentials')
  return response.data
}

/**
 * Test SmartAPI connection with provided credentials
 * @param {Object} credentials - { client_id, pin, totp_secret }
 * @returns {Promise<Object>} Test result with success status and message
 */
export async function testConnection(credentials) {
  const response = await api.post('/api/smartapi/test-connection', credentials)
  return response.data
}

/**
 * Authenticate with SmartAPI using stored credentials
 * @returns {Promise<Object>} Authentication result
 */
export async function authenticate() {
  const response = await api.post('/api/smartapi/authenticate')
  return response.data
}

/**
 * Get current market data source preference
 * @returns {Promise<Object>} { source, smartapi_configured, kite_configured }
 */
export async function getMarketDataSource() {
  const response = await api.get('/api/smartapi/market-data-source')
  return response.data
}

/**
 * Update market data source preference
 * @param {string} source - 'smartapi' or 'kite'
 * @returns {Promise<Object>} Updated source info
 */
export async function updateMarketDataSource(source) {
  const response = await api.put('/api/smartapi/market-data-source', { source })
  return response.data
}

export default {
  getCredentials,
  storeCredentials,
  deleteCredentials,
  testConnection,
  authenticate,
  getMarketDataSource,
  updateMarketDataSource
}
