import { createContext, useContext, useEffect } from "react";
import useLocalStorage from "../hooks/useLocalStorage";

/**
 * ThemeContext
 * ------------
 * Provides `theme` ("light" | "dark") and `toggleTheme()` to the whole
 * tree via useContext, so any component can read/flip the theme without
 * prop-drilling it down through every layer. The chosen theme is
 * persisted via useLocalStorage and applied to the <html> element as a
 * `data-theme` attribute, which app.css keys its color variables off of.
 */
const ThemeContext = createContext(undefined);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useLocalStorage("smart-task-manager:theme", "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (ctx === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}
