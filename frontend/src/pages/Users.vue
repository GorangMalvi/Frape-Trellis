<template>
  <div class="flex h-full flex-col">
    <header class="sp-glass-strong z-20 flex items-center gap-2.5 px-4 pt-4 md:px-6">
      <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--sp-fill)]">
        <LucideUsersRound class="h-4 w-4 sp-ink-2" />
      </span>
      <h1 class="sp-display text-[17px] font-semibold sp-ink-1">Users</h1>
      <div class="ml-auto">
        <AccentButton v-if="canManage" @click="inviteOpen = true">
          <template #prefix><LucideUserPlus class="h-4 w-4" /></template>
          Invite user
        </AccentButton>
      </div>
    </header>

    <main class="sp-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
      <EmptyState
        v-if="!canManage"
        title="Managers only"
        message="User management is available to workspace admins."
      >
        <template #icon><LucideLock class="h-6 w-6" /></template>
      </EmptyState>

      <template v-else>
        <!-- loading -->
        <div v-if="rows.loading && !rows.data" class="flex flex-col gap-2">
          <div v-for="i in 6" :key="i" class="sp-skeleton h-14 rounded-xl" />
        </div>

        <EmptyState
          v-else-if="rows.error"
          title="Couldn’t load users"
          :message="errorMessage(rows.error)"
        >
          <template #icon><LucideTriangleAlert class="h-6 w-6" /></template>
          <template #action><AccentButton @click="rows.reload()">Retry</AccentButton></template>
        </EmptyState>

        <div v-else class="overflow-hidden rounded-xl border sp-hair">
          <!-- header row -->
          <div class="grid grid-cols-[1fr,120px,110px,44px] items-center gap-3 border-b sp-hair bg-surface-gray-2 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide sp-ink-3 max-sm:hidden">
            <span>User</span>
            <span>Sprint Manager</span>
            <span>Status</span>
            <span />
          </div>

          <div
            v-for="u in rows.data || []"
            :key="u.name"
            class="border-b sp-hair px-4 py-2.5 last:border-0 max-sm:flex max-sm:flex-wrap max-sm:gap-y-2 sm:grid sm:grid-cols-[1fr,120px,110px,44px] sm:items-center sm:gap-3"
            :class="!u.enabled ? 'opacity-55' : ''"
          >
            <!-- identity -->
            <div class="flex min-w-0 items-center gap-2.5 max-sm:basis-full">
              <UserAvatar :user="u.name" size="lg" />
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="truncate text-sm font-medium sp-ink-1">{{ u.full_name || u.name }}</span>
                  <span v-if="u.is_admin" class="rounded bg-[var(--sp-fill-strong)] px-1.5 py-0.5 text-[10px] font-semibold sp-ink-2">ADMIN</span>
                </div>
                <div class="truncate text-xs sp-ink-3">{{ u.name }}</div>
              </div>
            </div>

            <!-- manager toggle -->
            <div>
              <label class="inline-flex cursor-pointer items-center gap-2" :class="u.is_admin ? 'cursor-not-allowed opacity-60' : ''">
                <input
                  type="checkbox"
                  class="rounded"
                  :checked="u.is_manager || u.is_admin"
                  :disabled="u.is_admin || busy[u.name]"
                  @change="toggleManager(u, $event.target.checked)"
                />
                <span class="text-xs sp-ink-3">{{ (u.is_manager || u.is_admin) ? 'Manager' : 'Member' }}</span>
              </label>
            </div>

            <!-- enabled toggle -->
            <div>
              <button
                class="inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium transition"
                :class="u.enabled ? 'bg-[var(--sp-fill)] sp-ink-2 hover:bg-[var(--sp-fill-hover)]' : 'bg-[var(--sp-fill)] sp-ink-3 hover:bg-[var(--sp-fill-hover)]'"
                :disabled="disableToggleDisabled(u) || busy[u.name]"
                @click="toggleEnabled(u)"
              >
                <span class="h-1.5 w-1.5 rounded-full" :class="u.enabled ? 'bg-ink-green-3' : 'bg-ink-gray-4'" />
                {{ u.enabled ? 'Active' : 'Disabled' }}
              </button>
            </div>

            <!-- actions -->
            <div class="flex justify-end max-sm:ml-auto">
              <button
                v-if="!u.is_admin"
                class="sp-control p-1.5"
                :disabled="busy[u.name]"
                title="Send set-password link"
                aria-label="Send set-password link"
                @click="sendReset(u)"
              >
                <LucideSend class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        <p class="mt-3 text-xs sp-ink-4">
          Disabled users can’t sign in and drop out of every assignee and access picker.
        </p>
      </template>
    </main>

    <InviteUserDialog v-if="inviteOpen" @close="inviteOpen = false" @created="onInvited" />
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { createResource, call } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import InviteUserDialog from '@/components/InviteUserDialog.vue'
import { session, users as userCache } from '@/lib/users'
import { pushToast, errorMessage } from '@/store'

const canManage = computed(() => session.canManage)
const inviteOpen = ref(false)
const busy = reactive({})

const rows = createResource({
  url: 'sprint.api.list_users',
  auto: canManage.value,
})

function disableToggleDisabled(u) {
  // can't disable yourself or the Administrator
  return u.is_admin || u.name === session.user
}

async function toggleManager(u, want) {
  if (u.is_admin) return
  busy[u.name] = true
  try {
    await call('sprint.api.set_user_role', { user: u.name, is_manager: want ? 1 : 0 })
    u.is_manager = want
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    busy[u.name] = false
  }
}

async function toggleEnabled(u) {
  if (disableToggleDisabled(u)) return
  busy[u.name] = true
  try {
    const res = await call('sprint.api.set_user_enabled', { user: u.name, enabled: u.enabled ? 0 : 1 })
    u.enabled = res.enabled
    // keep the shared directory in sync so pickers reflect the change
    userCache.loaded = false
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    busy[u.name] = false
  }
}

async function sendReset(u) {
  busy[u.name] = true
  try {
    const res = await call('sprint.api.send_user_reset', { user: u.name })
    pushToast(
      res.email_sent ? `Set-password link emailed to ${u.name}.` : `Reset link created for ${u.name} (email not configured).`,
      'success',
    )
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    busy[u.name] = false
  }
}

function onInvited() {
  rows.reload()
  userCache.loaded = false
}
</script>
