import { ref, onMounted, onUnmounted, watch } from 'vue';

/**
 * Composable for managing scroll indicators on scrollable containers.
 * Adds CSS classes 'can-scroll-left' and 'can-scroll-right' based on scroll position.
 * Use with the .scrollable-container class from style.css for shadow effects.
 *
 * @param {Ref<HTMLElement>} containerRef - Vue ref to the scrollable container element
 * @returns {Object} - { canScrollLeft, canScrollRight, updateScrollState }
 */
export function useScrollIndicator(containerRef) {
  const canScrollLeft = ref(false);
  const canScrollRight = ref(false);

  const updateScrollState = () => {
    if (!containerRef.value) return;

    const { scrollLeft, scrollWidth, clientWidth } = containerRef.value;

    // Check if there's content to scroll left
    canScrollLeft.value = scrollLeft > 0;

    // Check if there's content to scroll right (with 1px tolerance for rounding)
    canScrollRight.value = scrollLeft + clientWidth < scrollWidth - 1;

    // Toggle CSS classes for shadow effects
    containerRef.value.classList.toggle('can-scroll-left', canScrollLeft.value);
    containerRef.value.classList.toggle('can-scroll-right', canScrollRight.value);
  };

  // Watch for container ref changes
  watch(containerRef, (newVal) => {
    if (newVal) {
      newVal.addEventListener('scroll', updateScrollState);
      // Initial check after DOM settles
      setTimeout(updateScrollState, 100);
    }
  }, { immediate: true });

  onMounted(() => {
    if (containerRef.value) {
      containerRef.value.addEventListener('scroll', updateScrollState);
      window.addEventListener('resize', updateScrollState);
      // Initial check after DOM settles
      setTimeout(updateScrollState, 100);
    }
  });

  onUnmounted(() => {
    if (containerRef.value) {
      containerRef.value.removeEventListener('scroll', updateScrollState);
    }
    window.removeEventListener('resize', updateScrollState);
  });

  return { canScrollLeft, canScrollRight, updateScrollState };
}
