// Shared SortableJS options for every <draggable> so touch works: without a
// long-press delay a touch-drag starts on the first touchmove and fights
// scrolling. Spread with v-bind (a real object — vuedraggable mishandles
// falsy/kebab-string attrs, so never pass e.g. :force-fallback="false").
export const touchDragOptions = {
  delay: 250,
  delayOnTouchOnly: true,
  touchStartThreshold: 5,
  fallbackTolerance: 3,
  scrollSensitivity: 70,
  scrollSpeed: 12,
}
