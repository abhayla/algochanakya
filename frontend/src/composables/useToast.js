/**
 * Toast notification composable
 *
 * Simple toast notification system using browser alert() for now.
 * TODO: Replace with proper toast UI component library in future.
 */

export function useToast() {
  /**
   * Show a toast notification
   * @param {string} message - The message to display
   * @param {string} type - The type of toast (success, error, warning, info)
   */
  const showToast = (message, type = 'info') => {
    // Format message with type prefix
    const prefix = {
      success: '✓',
      error: '✗',
      warning: '⚠',
      info: 'ℹ'
    }[type] || 'ℹ'

    // Use browser alert for now
    // In production, this should be replaced with a proper toast library
    alert(`${prefix} ${message}`)
  }

  return {
    showToast
  }
}
