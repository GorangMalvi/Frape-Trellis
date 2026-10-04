<template>
  <div class="relative">
    <button
      class="flex w-full items-center gap-2.5 rounded-[10px] px-2 py-1.5 text-left transition hover:bg-[var(--sp-fill)]"
      @click="open = !open"
    >
      <UserAvatar :user="me" size="md" />
      <span class="min-w-0 flex-1">
        <span class="block truncate text-sm font-medium sp-ink-1">{{ name }}</span>
        <span class="block truncate text-[11px] sp-ink-3">{{ me }}</span>
      </span>
      <LucideChevronsUpDown class="h-3.5 w-3.5 shrink-0 sp-ink-3" />
    </button>

    <transition name="sp-pop">
      <div
        v-if="open"
        ref="panelEl"
        role="menu"
        class="sp-pop absolute bottom-full left-0 z-30 mb-1.5 w-full overflow-hidden p-1"
      >
        <button class="sp-menu-item" role="menuitem" @click="go('Account')">
          <LucideUser class="h-4 w-4" /> My account
        </button>
        <button v-if="isAdmin" class="sp-menu-item" role="menuitem" @click="go('Users')">
          <LucideUsersRound class="h-4 w-4" /> Manage users
        </button>
        <div class="my-1 border-t sp-hair" />
        <button class="sp-menu-item text-ink-red-3 hover:text-ink-red-3" role="menuitem" @click="signOut">
          <LucideLogOut class="h-4 w-4" /> Sign out
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import UserAvatar from '@/components/UserAvatar.vue'
import { session, currentUser, userLabel, ensureUsers } from '@/lib/users'
import { logout } from '@/lib/auth'
import { useOverlay } from '@/composables/useOverlay'

const router = useRouter()
const open = ref(false)
const panelEl = ref(null)
useOverlay({ close: () => (open.value = false), panel: panelEl, active: () => open.value })

const me = computed(() => currentUser())
const name = computed(() => userLabel(me.value) || me.value)
const isAdmin = computed(() => session.canManage)

ensureUsers()

function go(routeName) {
  open.value = false
  router.push({ name: routeName })
}
async function signOut() {
  open.value = false
  await logout()
}
</script>

<style scoped>
.sp-menu-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.5rem;
  padding: 0.375rem 0.5rem;
  text-align: left;
  font-size: 0.875rem;
  color: rgb(var(--sp-ink) / 0.75);
  transition: background 0.12s ease;
}
.sp-menu-item:hover {
  background: var(--sp-fill);
}
</style>
