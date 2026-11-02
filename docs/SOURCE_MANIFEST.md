# Source manifest

All records are generated synthetically by this repository. No external datasets, network calls, real names, or personal contact details are used. Synthetic identifiers are not derived from real records.

## Dashboard components and assets

The optional dashboard is a static React application. External component packages are used under their published licenses. No component was copied from 21st.dev; no API key or runtime external service is used. Retrieval date for the following npm packages and font assets: 2026-11-02. Exact package versions are pinned in `dashboard/package-lock.json`.

| Name | Author | URL | License | Retrieval date | Modifications |
|---|---|---|---|---|---|
| Radix UI Dialog, Select, Tooltip (`@radix-ui/react-*`) | Radix UI | https://www.radix-ui.com/primitives | MIT | 2026-11-02 | Used as accessibility and interaction primitives; composed into local shadcn-style wrappers and styled in `dashboard/src/App.tsx` and `dashboard/src/styles.css`. |
| TanStack React Table 8.21.3 | Tanner Linsley | https://tanstack.com/table | MIT | 2026-11-02 | Used as the decisions table model; local columns, owner grouping, pagination, and styling are implemented in this repository. |
| cmdk 1.1.1 | Paco | https://github.com/pacocoursey/cmdk | MIT | 2026-11-02 | Used for keyboard-filterable page navigation; local Radix dialog and visual styling are applied. |
| Recharts 3.10.1 | Recharts contributors | https://github.com/recharts/recharts | MIT | 2026-11-02 | Used for the demand/supply and forecast line charts; chart palette, axis treatment, tooltips, and as-of marker are locally styled. |
| lucide-react 1.66.0 | Lucide contributors | https://lucide.dev | ISC | 2026-11-02 | Package icons are used without modification. |
| Tailwind CSS 4.3.3 and `@tailwindcss/vite` 4.3.3 | Tailwind Labs | https://tailwindcss.com | MIT | 2026-11-02 | Tailwind is included through its Vite plugin and CSS entry point; application styling is local. |
| Geist Sans variable font (`@fontsource-variable/geist` 5.3.0) | Andrés Briganti, Mateo Zaragoza, Guillermo Rauch, Evil Rabbit, José Rago, Facundo Santana; distributed by Fontsource | https://fontsource.org/fonts/geist | SIL Open Font License 1.1 | 2026-11-02 | Latin variable WOFF2 asset is self-hosted under `dashboard/public/fonts`; the binary is unmodified. |
| Geist Mono variable font (`@fontsource-variable/geist-mono` 5.3.0) | Andrés Briganti, Mateo Zaragoza, Guillermo Rauch, Evil Rabbit, José Rago, Facundo Santana; distributed by Fontsource | https://fontsource.org/fonts/geist-mono | SIL Open Font License 1.1 | 2026-11-02 | Latin variable WOFF2 asset is self-hosted under `dashboard/public/fonts`; the binary is unmodified. |
| React and React DOM 19.3.1 | Meta Open Source | https://react.dev | MIT | 2026-11-02 | Application runtime; no upstream source is modified. |
