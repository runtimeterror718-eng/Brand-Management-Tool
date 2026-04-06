---
paths:
  - "oval/**/*.ts"
  - "oval/**/*.tsx"
  - "oval/**/*.css"
---

# Frontend Rules (OVAL Dashboard)

- Next.js 14 App Router with TypeScript — no pages/ router
- Tailwind CSS for all styling — no CSS modules or styled-components
- Supabase JS client for data access — defined in lib/
- Use `"use client"` directive only when component needs client-side interactivity
- API routes in `src/app/api/` follow Next.js route handler conventions
- Keep components in the app directory following Next.js colocation patterns
