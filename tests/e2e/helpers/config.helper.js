/**
 * Shared Test Configuration — Single Source of Truth for URLs
 *
 * Dev backend uses port 8001 (production uses 8000 — NEVER use 8000 for dev).
 * Import these constants instead of hardcoding URLs in test files.
 *
 * Usage:
 *   import { API_BASE, FRONTEND_URL, WS_BASE } from '../helpers/config.helper.js';
 */

export const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
export const API_BASE = process.env.API_BASE || 'http://localhost:8001';
export const WS_BASE = process.env.WS_BASE || 'ws://localhost:8001';
