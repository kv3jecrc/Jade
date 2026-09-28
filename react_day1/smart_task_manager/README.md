# Smart Task Manager

A small React "to-do list with a dashboard" built with Vite. Every
feature is implemented with React hooks rather than any external state
library.

## Features

- **Add Task** — a controlled form (title + priority: High/Medium/Low).
- **Display Task List** — each task shows its title, priority badge, and
  Completed/Pending status badge.
- **Mark as Completed** — a checkbox on each task toggles its status.
- **Delete Task** — a delete button removes a task permanently.
- **Search Tasks** — a search bar filters the list by title (case-insensitive, substring match).
- **Filter Tasks** — All / Completed / Pending view controls, combinable with search.
- **Theme Toggle** — a light/dark switch that restyles the whole UI via CSS custom properties, and remembers the choice across reloads.

## Which hooks do what

| Hook | Where | What it's for |
|---|---|---|
| `useState` | `TaskManager`, `TaskForm`, `ThemeToggle` (via context) | Local UI state: search term, active filter, form field values |
| `useLocalStorage` (custom, built on `useState` + `useEffect`) | `TaskManager` (tasks), `ThemeProvider` (theme) | Persists data to `localStorage` and hydrates from it on load |
| `useEffect` | inside `useLocalStorage`, and in `ThemeProvider` (applies `data-theme` to `<html>`) | Syncing state to the DOM / browser storage as a side effect |
| `useContext` (+ `createContext`) | `ThemeContext` → `useTheme()` | Shares theme state/toggle with any component without prop-drilling |
| `useMemo` | `TaskManager` (filtered+searched task list), `Dashboard` (stats) | Avoids recomputing derived data unless its actual inputs change |
| `useCallback` | `TaskManager` (add/toggle/delete handlers) | Stable handler identities passed down to list children |

## Project structure

```
src/
  hooks/
    useLocalStorage.js       custom hook: useState + useEffect, backed by localStorage
  context/
    ThemeContext.jsx         useContext-based theme provider (light/dark)
  components/
    Dashboard.jsx            stat cards: total, pending, completed, % done, priority breakdown
    TaskForm.jsx              add-task form
    SearchBar.jsx             search input
    FilterControls.jsx        All / Pending / Completed buttons
    TaskList.jsx / TaskItem.jsx   the rendered list
    ThemeToggle.jsx            light/dark switch
  App.jsx                     wires everything together, owns the task list state
  App.css                     theme variables (light/dark) + all component styling
```

## Design notes

- **Tasks and theme both persist** via the `useLocalStorage` hook, so
  refreshing the page doesn't lose your list or reset the theme. This
  wasn't explicitly required but makes the app feel like a real tool
  rather than a throwaway demo.
- **Dashboard is purely derived state** (`useMemo` over `tasks`) — it
  has no state of its own, so it can never show stale numbers.
- **Search and filter compose**: you can filter to "Pending" and search
  within that subset at the same time, since both are applied in the
  same `useMemo` pipeline in `App.jsx`.
- **Theming** uses CSS custom properties keyed off a `data-theme`
  attribute on `<html>` (set by `ThemeProvider`'s `useEffect`), so every
  component's colors update instantly without re-rendering React — only
  a CSS variable set changes.
- Task IDs are generated locally (timestamp + counter) since this is a
  client-only app with no backend.

## Running it

```bash
npm install
npm run dev       # local dev server
npm run build     # production build (verified passing)
npm run preview   # serve the production build
```

## Testing

No backend and no real users were available in the sandbox this was
built in, so verification was done with an automated headless-browser
test (Playwright) driving the built app through every feature end to
end: adding tasks, toggling completion, deleting, searching, filtering
(including search+filter combined), toggling theme, rejecting an
empty/whitespace title, and confirming both the task list and the theme
survive a page reload (localStorage persistence). All 21 checks passed
against the production build (`npm run build` + `npm run preview`). The
test script itself was a throwaway verification tool and isn't included
in this folder — the app was tested against real browser behavior, not
mocked.
