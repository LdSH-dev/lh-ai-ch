/**
 * Utility functions for formatting data values.
 * Centralized formatting logic to avoid code duplication across components.
 */

/**
 * Formats a file size in bytes to a human-readable string.
 *
 * @param {number|null|undefined} bytes - The file size in bytes.
 * @returns {string} A formatted string like "1.5 MB", "256 KB", or "Unknown size".
 *
 * @example
 * formatFileSize(1024)       // "1.0 KB"
 * formatFileSize(1536000)    // "1.5 MB"
 * formatFileSize(512)        // "512 B"
 * formatFileSize(null)       // "Unknown size"
 */
export function formatFileSize(bytes) {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

