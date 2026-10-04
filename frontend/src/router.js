import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
    meta: { public: true, noShell: true },
  },
  {
    path: '/update-password',
    name: 'UpdatePassword',
    component: () => import('@/pages/UpdatePassword.vue'),
    meta: { public: true, noShell: true },
  },
  {
    path: '/account',
    name: 'Account',
    component: () => import('@/pages/Account.vue'),
  },
  {
    path: '/admin/users',
    name: 'Users',
    component: () => import('@/pages/Users.vue'),
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/tickets/new',
    name: 'TicketIntake',
    component: () => import('@/pages/TicketIntake.vue'),
  },
  {
    path: '/tickets/:space',
    name: 'TicketBoard',
    component: () => import('@/pages/Board.vue'),
    props: (route) => ({ space: route.params.space, mode: 'ticket' }),
  },
  {
    path: '/:space/data',
    name: 'Data',
    component: () => import('@/pages/DataPage.vue'),
    props: true,
  },
  {
    path: '/:space/dashboard',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
    props: true,
  },
  {
    path: '/:space/automations',
    name: 'Automations',
    component: () => import('@/pages/Automations.vue'),
    props: true,
  },
  {
    path: '/:space?',
    name: 'Board',
    component: () => import('@/pages/Board.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory('/sprint'),
  routes,
})

// Auth gate: guests may only see `public` routes (login / set-password); every
// other route bounces to the in-app login, preserving where they were headed.
// Signed-in users are kept off the login screen.
router.beforeEach((to) => {
  const guest = !window.user || window.user === 'Guest'
  if (guest && !to.meta.public) {
    return { name: 'Login', query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  if (!guest && to.name === 'Login') {
    return { name: 'Home' }
  }
  return true
})

export default router
