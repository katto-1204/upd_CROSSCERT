/**
 * API Configuration for CROSSCERT
 * Uses dashes (kebab-case) for all route names
 */

// Base API URL - can be configured via environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * API Route paths using dashes (kebab-case)
 */
export const API_ROUTES = {
  // General API routes
  events: '/api/events',
  registrations: '/api/registrations',
  checkIns: '/api/check-ins',
  evaluations: '/api/evaluations',
  certificates: '/api/certificates',
  
  // Admin API routes (using dashes)
  admin: {
    events: '/api/admin/events',
    participants: '/api/admin/participants',
    checkIns: '/api/admin/check-ins',
    evaluations: '/api/admin/evaluations',
    certificates: '/api/admin/certificates',
  },
} as const

/**
 * Get full API URL for a route
 */
export function getApiUrl(route: string): string {
  return `${API_BASE_URL}${route}`
}

/**
 * Admin API helper functions
 */
export const adminApi = {
  events: () => getApiUrl(API_ROUTES.admin.events),
  participants: () => getApiUrl(API_ROUTES.admin.participants),
  checkIns: () => getApiUrl(API_ROUTES.admin.checkIns),
  evaluations: () => getApiUrl(API_ROUTES.admin.evaluations),
  certificates: () => getApiUrl(API_ROUTES.admin.certificates),
  
  // Helper to get a specific event by ID
  eventById: (id: string | number) => `${getApiUrl(API_ROUTES.admin.events)}/${id}/`,
  
  // Helper to get a specific participant by ID
  participantById: (id: string | number) => `${getApiUrl(API_ROUTES.admin.participants)}/${id}/`,
  
  // Helper to get check-ins for an event
  checkInsByEvent: (eventId: string | number) => `${getApiUrl(API_ROUTES.admin.checkIns)}/?event=${eventId}`,
}

/**
 * General API helper functions
 */
export const api = {
  events: () => getApiUrl(API_ROUTES.events),
  registrations: () => getApiUrl(API_ROUTES.registrations),
  checkIns: () => getApiUrl(API_ROUTES.checkIns),
  evaluations: () => getApiUrl(API_ROUTES.evaluations),
  certificates: () => getApiUrl(API_ROUTES.certificates),
  participants: () => getApiUrl('/api/participants'),
  
  // Helper to get a specific resource by ID
  eventById: (id: string | number) => `${getApiUrl(API_ROUTES.events)}/${id}/`,
  registrationById: (id: string | number) => `${getApiUrl(API_ROUTES.registrations)}/${id}/`,
  certificateById: (id: string | number) => `${getApiUrl(API_ROUTES.certificates)}/${id}/`,
}

