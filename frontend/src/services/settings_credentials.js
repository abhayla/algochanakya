/**
 * Settings Credentials Service
 *
 * API calls for the Settings page OAuth connections.
 * These use /api/settings/{broker}/connect (NOT /api/auth/{broker}/login)
 * to avoid overwriting the user's current login session.
 */
import api from './api'

/**
 * Get the Settings OAuth URL for a broker and redirect to it.
 * @param {string} broker - 'zerodha' | 'upstox' | 'fyers' | 'paytm'
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function initiateSettingsConnect(broker) {
  try {
    const response = await api.get(`/api/settings/${broker}/connect`)
    window.location.href = response.data.login_url
    return { success: true }
  } catch (err) {
    return {
      success: false,
      error: err.response?.data?.detail || `Failed to connect ${broker}`,
    }
  }
}
