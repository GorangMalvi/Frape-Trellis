<template>
  <header class="sp-glass-strong relative z-30 flex shrink-0 items-center gap-1 border-b sp-hair px-2 pb-2 pt-[calc(env(safe-area-inset-top)+0.5rem)] md:hidden">
    <button
      class="sp-control flex h-9 w-9 items-center justify-center"
      aria-label="Open menu"
      @click="toggleSidebar"
    >
      <LucideMenu class="h-5 w-5" />
    </button>
    <div class="flex h-6 w-6 items-center justify-center rounded-[8px] bg-gradient-to-b from-[#0a84ff] to-[#0071e3] text-xs font-bold text-white shadow-sm">
      S
    </div>
    <span class="sp-display truncate text-[15px] font-semibold sp-ink-1">SASAGEYO</span>
    <div class="flex-1" />
    <button
      class="sp-control flex h-9 w-9 items-center justify-center"
      aria-label="Search"
      @click="openPalette"
    >
      <LucideSearch class="h-[18px] w-[18px]" />
    </button>
    <button
      class="sp-control flex h-9 w-9 items-center justify-center"
      aria-label="New task"
      @click="triggerNewTask"
    >
      <LucidePlus class="h-5 w-5" />
    </button>
  </header>
</template>

<script setup>
import { openPalette, toggleSidebar, triggerNewTask } from '@/store'
</script>
