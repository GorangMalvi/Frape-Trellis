<template>
  <div class="lg-auth-bg" :style="{ backgroundImage: `url(${loginBg})` }">
    <div class="h-full overflow-y-auto">
      <div class="flex min-h-full items-center justify-center px-4 py-12">
        <div class="w-full max-w-[400px]">
          <!-- brand (on the gradient, not the glass) -->
          <div class="mb-8 flex flex-col items-center gap-3">
            <div class="flex h-12 w-12 items-center justify-center rounded-[14px] bg-white/90 text-lg font-bold text-[#0071e3] shadow-lg backdrop-blur">
              S
            </div>
            <h1 class="lg-auth-title text-xl font-semibold">
              {{ mode === 'signin' ? 'Welcome Back, Wanderer' : 'Reset your password' }}
            </h1>
            <p v-if="mode === 'forgot'" class="lg-auth-sub -mt-1 text-center text-sm">
              Enter your email and we’ll send you a reset link.
            </p>
          </div>

          <!-- liquid-glass card (draggable — slide it over the artwork to play
               with the refraction) -->
          <div
            ref="cardEl"
            class="lg-auth-card p-6"
            :class="{ dragging }"
            :style="{ transform: `translate(${pos.x}px, ${pos.y}px)` }"
            @pointerdown="startDrag"
            @pointermove="onDrag"
            @pointerup="endDrag"
            @pointercancel="endDrag"
          >
            <div class="lg-grip" title="Drag to move · double-click to recenter" @dblclick="resetPos" />
            <!-- sign in -->
            <form v-if="mode === 'signin'" @submit.prevent="submit">
              <label class="lg-label">Email or username</label>
              <input
                ref="emailEl"
                v-model="email"
                type="text"
                autocomplete="username"
                placeholder="you@company.com"
                class="lg-input mb-3"
              />
              <label class="lg-label">Password</label>
              <input
                v-model="password"
                type="password"
                autocomplete="current-password"
                placeholder="••••••••"
                class="lg-input"
              />

              <p v-if="error" class="lg-error">{{ error }}</p>

              <button type="submit" class="lg-primary mt-5" :disabled="loading">
                <LucideLoader2 v-if="loading" class="h-4 w-4 animate-spin" />
                <span>Sign in</span>
              </button>

              <button type="button" class="lg-textbtn mt-4" @click="switchMode('forgot')">
                Forgot your password?
              </button>
            </form>

            <!-- forgot password -->
            <form v-else @submit.prevent="sendReset">
              <template v-if="!sent">
                <label class="lg-label">Email</label>
                <input
                  ref="forgotEl"
                  v-model="email"
                  type="email"
                  autocomplete="username"
                  placeholder="you@company.com"
                  class="lg-input"
                />
                <p v-if="error" class="lg-error">{{ error }}</p>
                <button type="submit" class="lg-primary mt-5" :disabled="loading">
                  <LucideLoader2 v-if="loading" class="h-4 w-4 animate-spin" />
                  <span>Send reset link</span>
                </button>
              </template>

              <div v-else class="flex flex-col items-center gap-2 py-2 text-center">
                <div class="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white">
                  <LucideMailCheck class="h-5 w-5" />
                </div>
                <p class="text-sm text-white/85">
                  If that email is registered, a reset link is on its way. Check your inbox.
                </p>
              </div>

              <button type="button" class="lg-textbtn mt-4 flex items-center justify-center gap-1.5" @click="switchMode('signin')">
                <LucideArrowLeft class="h-3.5 w-3.5" /> Back to sign in
              </button>
            </form>
          </div>

          <p class="lg-auth-footer mt-6 text-center text-[11px]">
            Developed by <span class="font-medium">Manas</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { login, requestPasswordReset } from '@/lib/auth'
import { errorMessage } from '@/store'
import { useLiquidGlass } from '@/composables/useLiquidGlass'
import loginBg from '@/assets/login-bg.webp'

const route = useRoute()

const mode = ref('signin')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)
const emailEl = ref(null)
const forgotEl = ref(null)
const cardEl = ref(null)

// The signature effect: the card refracts the colourful gradient behind it
// (Chromium; frosted fallback on Safari/Firefox).
useLiquidGlass(cardEl, { scale: -120, chroma: 7, border: 0.06, mapBlur: 14, blur: 3, saturate: 1.8, radius: 26 })

onMounted(() => nextTick(() => emailEl.value?.focus()))

// ---- draggable card ----------------------------------------------------
// Slide the glass card around over the artwork; the backdrop refraction
// re-samples live as it moves. Drags from any non-interactive area (inputs and
// buttons stay clickable); clamped on-screen; double-click the grip to recenter.
const pos = reactive({ x: 0, y: 0 })
const dragging = ref(false)
let drag = null

function startDrag(e) {
  // touch: the drag gimmick would swallow scroll gestures — keep the card static
  if (window.matchMedia('(pointer: coarse)').matches) return
  if (e.target.closest('input,button,select,textarea,a')) return
  const rect = cardEl.value.getBoundingClientRect()
  drag = {
    id: e.pointerId,
    px: e.clientX,
    py: e.clientY,
    baseLeft: rect.left - pos.x, // card's left with the transform removed
    baseTop: rect.top - pos.y,
    w: rect.width,
    h: rect.height,
  }
  cardEl.value.setPointerCapture?.(e.pointerId)
  dragging.value = true
  e.preventDefault()
}

function onDrag(e) {
  if (!drag) return
  const m = 8 // keep this much of a gap from the viewport edges
  const left = Math.min(Math.max(drag.baseLeft + (e.clientX - drag.px), m), window.innerWidth - drag.w - m)
  const top = Math.min(Math.max(drag.baseTop + (e.clientY - drag.py), m), window.innerHeight - drag.h - m)
  pos.x = left - drag.baseLeft
  pos.y = top - drag.baseTop
}

function endDrag() {
  if (!drag) return
  cardEl.value?.releasePointerCapture?.(drag.id)
  drag = null
  dragging.value = false
}

function resetPos() {
  pos.x = 0
  pos.y = 0
}

function switchMode(m) {
  mode.value = m
  error.value = ''
  sent.value = false
  nextTick(() => (m === 'forgot' ? forgotEl.value : emailEl.value)?.focus())
}

async function submit() {
  error.value = ''
  if (!email.value.trim() || !password.value) {
    error.value = 'Enter your email and password.'
    return
  }
  loading.value = true
  try {
    const redirect = route.query.redirect
    await login(email.value.trim(), password.value, typeof redirect === 'string' ? redirect : '/')
  } catch (e) {
    error.value = errorMessage(e, 'Could not sign in. Check your email and password.')
    loading.value = false
  }
}

async function sendReset() {
  error.value = ''
  if (!email.value.trim()) {
    error.value = 'Enter your email.'
    return
  }
  loading.value = true
  try {
    await requestPasswordReset(email.value.trim())
    sent.value = true
  } catch (e) {
    error.value = errorMessage(e, 'Could not send the reset link. Please try again.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Photographic backdrop (bundled image, set inline) so the glass card has rich,
 * dark content to refract. Cover + center; dark fallback colour while it loads. */
.lg-auth-bg {
  height: 100%;
  width: 100%;
  position: relative;
  overflow: hidden;
  background-color: #14141c;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.lg-auth-title {
  color: #fff;
  text-shadow: 0 1px 6px rgb(0 0 0 / 0.5);
}
.lg-auth-sub {
  color: rgb(255 255 255 / 0.85);
  text-shadow: 0 1px 4px rgb(0 0 0 / 0.5);
}
.lg-auth-footer {
  color: rgb(255 255 255 / 0.75);
  text-shadow: 0 1px 4px rgb(0 0 0 / 0.5);
}
.lg-auth-footer .font-medium {
  color: #fff;
}

/* smoked-glass panel — translucent dark so refraction reads over a dark photo;
 * liquidGlass adds the backdrop-filter (SVG displacement + blur + saturate)
 * inline. White rim + top specular highlight sell the glass edge. */
.lg-auth-card {
  border-radius: 26px;
  background: rgb(22 22 30 / 0.26);
  box-shadow: 0 30px 70px -22px rgb(0 0 0 / 0.6), 0 8px 22px -12px rgb(0 0 0 / 0.5),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.35), inset 0 1.5px 0 rgb(255 255 255 / 0.5);
  cursor: grab; /* draggable from any non-interactive area */
  touch-action: none; /* let pointer-drag own the gesture on touch */
  will-change: transform;
}
.lg-auth-card.dragging {
  cursor: grabbing;
  user-select: none;
}
/* grip handle at the top — the obvious "grab me" affordance */
.lg-grip {
  width: 40px;
  height: 5px;
  margin: -2px auto 14px;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.4);
  cursor: grab;
}
.lg-auth-card.dragging .lg-grip {
  cursor: grabbing;
}
/* where refraction isn't supported, a denser frost keeps it legible */
.lg-auth-card.lg-fallback {
  background: rgb(22 22 30 / 0.5);
}
/* touch devices: dragging is disabled, so scrolling over the card must work */
@media (pointer: coarse) {
  .lg-auth-card {
    touch-action: auto;
    cursor: default;
  }
  .lg-grip {
    display: none;
  }
}

.lg-label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(255 255 255 / 0.8);
}
.lg-input {
  height: 2.5rem;
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid rgb(255 255 255 / 0.25);
  background: rgb(255 255 255 / 0.12);
  padding: 0 0.75rem;
  font-size: 0.875rem;
  color: #fff;
}
.lg-input::placeholder {
  color: rgb(255 255 255 / 0.5);
}
.lg-input:focus {
  outline: none;
  border-color: #4da3ff;
  background: rgb(255 255 255 / 0.18);
}
.lg-error {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: #ff8a80;
  font-weight: 500;
}

.lg-primary {
  display: flex;
  height: 2.5rem;
  width: 100%;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border-radius: 0.5rem;
  background: linear-gradient(180deg, #0a84ff, #0071e3);
  font-size: 0.875rem;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 6px 16px -6px rgb(0 113 227 / 0.6), inset 0 1px 0 rgb(255 255 255 / 0.4);
  transition: filter 0.15s ease, transform 0.1s ease;
}
.lg-primary:hover {
  filter: brightness(1.05);
}
.lg-primary:active {
  transform: translateY(0.5px);
}
.lg-primary:disabled {
  opacity: 0.7;
  cursor: default;
}

.lg-textbtn {
  display: block;
  width: 100%;
  text-align: center;
  font-size: 0.875rem;
  color: rgb(255 255 255 / 0.72);
  transition: color 0.15s ease;
}
.lg-textbtn:hover {
  color: #fff;
}
</style>
