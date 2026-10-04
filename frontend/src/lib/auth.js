// In-app authentication for the Sprint SPA. Login/logout use Frappe's built-in
// /api/method/login + /api/method/logout. Keeps operators off Frappe Desk's
// native login (B2B SaaS).
//
// Why hard reloads: logging in rotates the session and its CSRF token, but
// window.csrf_token still holds the pre-login (guest) token. Any JS API call
// before a reload would send that stale token and be rejected with a
// CSRFTokenError. A full navigation re-serves the SPA under the new session, so
// window.user + window.csrf_token come back fresh from the boot injection.
import { call } from 'frappe-ui'

// The router history base is /sprint, so an app path of "/foo" lives at
// "/sprint/foo" and the app root at "/sprint/".
function appUrl(path) {
  if (!path || path === '/' || !path.startsWith('/')) return '/sprint/'
  return '/sprint' + path
}

export async function login(email, password, redirectPath = '/') {
  await call('login', { usr: email, pwd: password })
  window.location.href = appUrl(redirectPath)
}

export async function logout() {
  try {
    await call('logout')
  } catch {
    /* even if the call fails, fall through to a hard reset */
  }
  window.location.href = '/sprint/login'
}

export function requestPasswordReset(email) {
  return call('sprint.api.request_password_reset', { email })
}

export function setPasswordWithKey(key, newPassword) {
  return call('sprint.api.set_password_with_key', { key, new_password: newPassword })
}

// Is nobody signed in? Boot seeds window.user; Frappe uses the literal "Guest".
export function isGuest() {
  const u = (typeof window !== 'undefined' && window.user) || ''
  return !u || u === 'Guest'
}
