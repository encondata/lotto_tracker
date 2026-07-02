import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * GSAP-driven count-up. Returns the current numeric value, animating from 0
 * to `target` on mount (and whenever target changes). Respects reduced motion.
 */
export function useCountUp(target: number, duration = 1.1): number {
  const [value, setValue] = useState(prefersReducedMotion() ? target : 0)
  const objRef = useRef({ v: 0 })

  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target)
      return
    }
    const obj = objRef.current
    const tween = gsap.to(obj, {
      v: target,
      duration,
      ease: 'power2.out',
      onUpdate: () => setValue(obj.v),
    })
    return () => {
      tween.kill()
    }
  }, [target, duration])

  return value
}
