import { watch, onBeforeUnmount, nextTick } from 'vue'
import liquidGlass from '@/lib/liquidGlass'

/**
 * Attach the liquid-glass refraction effect to an element ref, managing its
 * lifecycle. Pass `active` (a getter) for overlays that mount/unmount (the
 * effect is applied when it becomes true and torn down when false); omit it to
 * apply once on mount. Always cleaned up on unmount.
 *
 * @param {import('vue').Ref<Element|null>} panelRef  the target element ref
 * @param {Object}   [opts]    liquidGlass options (scale, blur, saturate, …)
 * @param {Function} [active]  () => boolean; when provided, drives apply/destroy
 */
export function useLiquidGlass(panelRef, opts = {}, active = null) {
  let handle = null

  function apply() {
    if (handle || !panelRef.value) return
    handle = liquidGlass(panelRef.value, opts)
  }
  function remove() {
    handle?.destroy?.()
    handle = null
  }

  if (active) {
    watch(active, (on) => (on ? nextTick(apply) : remove()), { immediate: true })
  } else {
    nextTick(apply)
  }

  onBeforeUnmount(remove)
  return { refresh: () => handle?.refresh?.() }
}
