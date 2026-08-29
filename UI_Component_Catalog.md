# ApplyFlow ATS — Complete UI Component Catalog & Design System

> **Design Tokens Standard**: Tailwind CSS v4 + Semantic CSS Variables  
> **Typeface**: Inter (`sans-serif`), Monospace (`ui-monospace, SFMono-Regular, Menlo, Monaco`)  
> **Base Canvas**: `#F6F8FB` (Light Workspace), `#081226` (Dark Navy Foundations)

---

## 1. Visual Token Foundations

### 1.1 Color Palette Tokens

```css
/* Dark Navy Surfaces (Sidebar, Modals, Overlays) */
--color-navy:                  #081226;
--color-navy-dark:             #040A17;
--color-navy-light:            #101F3D;
--color-navy-border:           #1E2E4E;

/* Interactive Primary & Brand Colors */
--color-blue-primary:          #2563EB;
--color-blue-hover:            #1D4ED8;
--color-blue-subtle:           #EFF6FF;
--color-blue-border:           #BFDBFE;

/* Quota & Live Progress Accents */
--color-orange-progress:       #F97316;
--color-orange-subtle:         #FFF7ED;
--color-orange-border:         #FFEDD5;

/* Light Canvas Foundations */
--color-bg-main:               #F6F8FB;
--color-surface-white:         #FFFFFF;
--color-surface-muted:         #F8FAFC;
--color-surface-border:        #E2E8F0;
--color-surface-border-subtle: #F1F5F9;

/* Semantic Status Signals */
--color-status-success:        #16A34A;
--color-status-success-bg:     #F0FDF4;
--color-status-success-border: #BBF7D0;

--color-status-warning:        #F59E0B;
--color-status-warning-bg:     #FFFBEB;
--color-status-warning-border: #FDE68A;

--color-status-danger:         #EF4444;
--color-status-danger-bg:      #FEF2F2;
--color-status-danger-border:  #FECACA;

/* Typography Text Colors */
--color-text-main:             #081226;
--color-text-secondary:        #475569;
--color-text-muted:            #94A3B8;
--color-text-dim:              #CBD5E1;
```

---

## 2. Atomic Component Specifications

### 2.1 `Avatar.jsx`
- **File Location**: `frontend/src/components/ui/Avatar.jsx`
- **Purpose**: Displays user or candidate initials with deterministic color variants and online status dots.
- **Props**:
  | Prop | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | `name` | `string` | `'User'` | Full name from which 1–2 uppercase initials are extracted. |
  | `size` | `'xs' \| 'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | `xs` (24px), `sm` (32px), `md` (40px), `lg` (48px), `xl` (56px). |
  | `variant` | `'blue' \| 'purple' \| 'teal' \| 'orange' \| 'navy'` | `'blue'` | Color theme for avatar background. |
  | `status` | `'online' \| 'offline' \| 'busy' \| null` | `null` | Optional corner indicator dot. |
- **Accessibility**: Sets `aria-label={name}` and `role="img"`.

---

### 2.2 `Button.jsx`
- **File Location**: `frontend/src/components/ui/Button.jsx`
- **Purpose**: Primary interactive trigger supporting multiple visual weights and async loading states.
- **Variants**:
  - `primary`: Solid `#2563EB` with hover `#1D4ED8` and shadow.
  - `secondary`: Deep Navy `#081226` with hover `#101F3D`.
  - `outline`: White background with `#E2E8F0` border and slate text.
  - `ghost`: Transparent background with soft `#F1F5F9` hover tint.
  - `danger`: Solid `#EF4444` for destructive actions.
  - `success`: Solid `#16A34A` for confirmations.
- **Props**: `variant`, `size`, `isLoading`, `leftIcon`, `rightIcon`, `disabled`, `children`.
- **Loading Behavior**: Renders inline SVG spinner, preserves button width, and sets `aria-busy="true"`.

---

### 2.3 `KPICard.jsx`
- **File Location**: `frontend/src/components/ui/KPICard.jsx`
- **Purpose**: Metric display card for dashboard overviews.
- **Props**:
  | Prop | Type | Description |
  | :--- | :--- | :--- |
  | `title` | `string` | Metric label (e.g. "Today's Uploads"). |
  | `value` | `string \| number` | Large display number or formatted text. |
  | `subtitle` | `string` | Sub-label or contextual comparison (e.g. "+12 from yesterday"). |
  | `icon` | `LucideIcon` | Leading icon enclosed in a soft-tinted squircle. |
  | `colorScheme` | `'blue' \| 'orange' \| 'green' \| 'purple' \| 'red'` | Theming for icon background and subtle border glow. |
  | `trend` | `string` | Optional percentage string (e.g. "+14.2%"). |
  | `trendDirection` | `'up' \| 'down'` | Directs green up-arrow or red down-arrow. |

---

### 2.4 `ProgressRing.jsx`
- **File Location**: `frontend/src/components/ui/ProgressRing.jsx`
- **Purpose**: SVG circular progress meter specifically engineered for daily targets.
- **Props**:
  | Prop | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | `percentage` | `number` | `0` | Completion percentage (supports values > 100%). |
  | `size` | `number` | `120` | Diameter in pixels. |
  | `strokeWidth` | `number` | `10` | Track thickness. |
  | `showLabel` | `boolean` | `true` | Centers text percentage in ring center. |
- **Dynamic Thresholds**:
  - `0% - 50%`: Danger Red (`#EF4444`)
  - `51% - 99%`: Progress Orange (`#F97316`)
  - `100%+`: Success Emerald (`#16A34A`) with glowing SVG filter.

---

### 2.5 `DateFilter.jsx`
- **File Location**: `frontend/src/components/ui/DateFilter.jsx`
- **Purpose**: Universal cascading date range selector.
- **Props**:
  | Prop | Type | Description |
  | :--- | :--- | :--- |
  | `value` | `string` | Active preset or ISO date string (`today`, `yesterday`, `this_week`, `this_month`, `YYYY-MM-DD`). |
  | `onChange` | `(val: string) => void` | Event callback emitted on selection. |
- **Sub-Units**: Preset pills, native HTML5 `<input type="date">` picker popover.

---

### 2.6 `UploadDropzone.jsx`
- **File Location**: `frontend/src/components/ui/UploadDropzone.jsx`
- **Purpose**: Drag-and-drop batch file ingestion container.
- **Features**:
  - Multi-file drop handling up to 100+ files.
  - Client-side MIME validation (`application/pdf`).
  - Active drag-over pulse animation (`border-[#2563EB] bg-[#EFF6FF]/60`).
  - Native file explorer browse button fallback.

---

### 2.7 `Table.jsx`
- **File Location**: `frontend/src/components/ui/Table.jsx`
- **Purpose**: High-density enterprise data grid.
- **Features**:
  - Sticky table headers with subtle border separators.
  - Alternating zebra row hover highlights.
  - Empty state fallback (`EmptyState.jsx`) when `data.length === 0`.
  - Built-in pagination footer (Page X of Y, Prev/Next buttons, Page Size selector).

---

### 2.8 `Modal.jsx`
- **File Location**: `frontend/src/components/ui/Modal.jsx`
- **Purpose**: Accessible dialog overlay.
- **Features**:
  - Framer Motion scale-up entrance animation (`initial: { scale: 0.95, opacity: 0 }`).
  - Focus trap preventing background tabbing.
  - `Escape` key and backdrop click dismissal.
  - Backdrop blur filter (`backdrop-blur-md bg-black/60`).

---

### 2.9 `CommandPalette.jsx`
- **File Location**: `frontend/src/components/ui/CommandPalette.jsx`
- **Purpose**: Spotlight `⌘K` search dialog.
- **Keybindings**:
  - `⌘K` / `Ctrl+K`: Opens palette.
  - `↑` / `↓`: Navigates search results.
  - `Enter`: Navigates to selected candidate, client, or job.
  - `Esc`: Closes palette.

---

### 2.10 `StatusBadge.jsx`
- **File Location**: `frontend/src/components/ui/StatusBadge.jsx`
- **Purpose**: Color-coded rounded stage indicator.
- **Props**: `status` (string), `size` (`'sm' | 'md'`).
- **Semantic Mappings**:
  - `Submitted` $\rightarrow$ Soft Blue (`bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]`)
  - `Shortlisted` $\rightarrow$ Soft Purple (`bg-[#F5F3FF] text-[#7C3AED] border-[#DDD6FE]`)
  - `Round 1` / `Round 2` / `Technical` $\rightarrow$ Progress Orange (`bg-[#FFF7ED] text-[#F97316] border-[#FFEDD5]`)
  - `Offer` / `Joined` $\rightarrow$ Success Green (`bg-[#F0FDF4] text-[#16A34A] border-[#BBF7D0]`)
  - `Rejected` $\rightarrow$ Danger Red (`bg-[#FEF2F2] text-[#EF4444] border-[#FECACA]`)

---

### 2.11 `Toast.jsx` & `ToastProvider`
- **File Location**: `frontend/src/components/ui/Toast.jsx`
- **Purpose**: Non-blocking toast notification stack.
- **Hook**: `useToast()` exposing `success(title, msg)`, `error(title, msg)`, `warning(title, msg)`, `info(title, msg)`.
- **Behavior**: Stacks in bottom-right corner with smooth exit transitions and 4000ms auto-dismiss timer.

---

### 2.12 `BrandedLoader.jsx`
- **File Location**: `frontend/src/components/ui/BrandedLoader.jsx`
- **Purpose**: Brand-aligned loading indicator for Suspense boundaries and route transitions.
- **Visuals**: Dark Navy rounded badge (`#081226`) with spinning electric blue border (`#2563EB`) and glowing logo element.
