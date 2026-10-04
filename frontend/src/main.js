import './index.css'

import { createApp } from 'vue'
import { FrappeUI, setConfig, frappeRequest, initSocket } from 'frappe-ui'
import router from './router'
import App from './App.vue'
import { setSocket, initTheme } from './store'
import { setCurrentUser, setCanManage } from './lib/users'
import glass from './directives/glass'

// resolve appearance (Auto/Light/Dark) + accent and apply to <html> before mount
initTheme()

const app = createApp(App)

// If the session has expired mid-use, an API call comes back as a "not logged
// in" error. Bounce to the in-app login (never Frappe Desk) and return here
// afterwards. We only do this for genuine auth failures, never for ordinary
// permission denials.
async function authedRequest(options) {
  try {
    return await frappeRequest(options)
  } catch (e) {
    const text = [e?.exc_type, ...(e?.messages || []), e?.message].filter(Boolean).join(' ')
    const notLoggedIn = /not whitelisted|Login to access|Session (Expired|Stopped)/i.test(text)
    const cur = router.currentRoute.value
    if (notLoggedIn && cur.name !== 'Login' && cur.name !== 'UpdatePassword') {
      window.user = 'Guest' // so the router guard treats the stale session as signed-out
      router.replace({ name: 'Login', query: cur.fullPath && cur.fullPath !== '/' ? { redirect: cur.fullPath } : {} })
      return new Promise(() => {}) // halt the chain while we navigate away
    }
    if (notLoggedIn) return new Promise(() => {})
    throw e
  }
}

setConfig('resourceFetcher', authedRequest)
app.use(FrappeUI)
app.use(router)
app.directive('glass', glass)

function start() {
  // seed session identity + structural rights from the boot vars
  setCurrentUser(window.user)
  setCanManage(window.can_manage)
  // realtime: connect after window.* boot vars are available
  try {
    const socket = initSocket()
    setSocket(socket)
    app.config.globalProperties.$socket = socket
  } catch (e) {
    console.warn('Sprint: realtime socket unavailable', e)
  }
  app.mount('#app')
}

// In dev (vite server) there is no jinja boot injection, so pull csrf_token,
// user and basics from the backend before mounting. In production the
// frappe-ui vite plugin injects boot data into the served HTML.
if (import.meta.env.DEV) {
  frappeRequest({ url: '/api/method/sprint.www.sprint.get_context_for_dev' })
    .then((values) => {
      for (const key in values) window[key] = values[key]
      start()
    })
    .catch(start)
} else {
  start()
}
