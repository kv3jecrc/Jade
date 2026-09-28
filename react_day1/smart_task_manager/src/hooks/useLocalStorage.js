import { useState, useEffect } from "react";

/**
 * useLocalStorage
 * ----------------
 * A small custom hook that behaves like useState but persists its value
 * to localStorage under `key`, and hydrates from localStorage on mount.
 * Used for both the task list and the theme preference so a page refresh
 * doesn't wipe the user's data or force them back to the light theme.
 */
export default function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key);
      return stored !== null ? JSON.parse(stored) : initialValue;
    } catch (err) {
      console.warn(`useLocalStorage: failed to read key "${key}"`, err);
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
      console.warn(`useLocalStorage: failed to write key "${key}"`, err);
    }
  }, [key, value]);

  return [value, setValue];
}
