---
name: nextjs-building
description: Next.js 16+ App Router building with React 19, Server Components ("use client"/"use server"), useActionState, Turbopack, and SSR/SSG patterns. Use when creating page.tsx, layout.tsx, loading.tsx, route handlers, server actions, or fixing hydration errors. Apply for .tsx files in app/, components/, lib/, or next.config.ts. (project)
---

# Next.js Frontend Development

Modern patterns for Next.js 16 with React 19 and App Router (December 2025 best practices).

**Package Manager:** Use `pnpm` for all Node.js projects.

## When To Apply

- Creating or editing pages and layouts
- Building React components
- Implementing server actions
- Setting up data fetching with TanStack Query
- Debugging hydration or rendering issues

## Quick Reference

| Pattern | Current (Dec 2025) | Notes |
|---------|-------------------|-------|
| Bundler | Turbopack (default) | 5x faster builds |
| Components | Server Components (default) | `"use client"` for interactivity |
| Data fetching | TanStack Query + Server Actions | Not `getServerSideProps` |
| Caching | `use cache` directive | New in Next.js 16 |
| Forms | `useActionState` + Server Actions | React 19 pattern |
| Memoization | React Compiler (auto) | No manual `useMemo` |

---

## Project Structure (App Router)

```
apps/web/
├── app/                    # App Router pages
│   ├── layout.tsx          # Root layout (required)
│   ├── page.tsx            # Home page
│   ├── loading.tsx         # Suspense fallback
│   ├── error.tsx           # Error boundary
│   ├── not-found.tsx       # 404 page
│   ├── (dashboard)/        # Route group (no URL segment)
│   │   ├── layout.tsx
│   │   └── products/
│   │       ├── page.tsx
│   │       └── [id]/
│   │           └── page.tsx
│   └── api/                # Route handlers
│       └── health/
│           └── route.ts
├── components/             # Shared components
│   ├── ui/                 # shadcn/ui components
│   └── features/           # Feature-specific
├── lib/                    # Utilities
│   ├── api-client.ts       # SDK client setup
│   └── utils.ts
└── next.config.ts          # TypeScript config
```

---

## Server vs Client Components

### Server Components (Default)

```tsx
// app/products/page.tsx - Server Component by default
import { getProducts } from '@/lib/api'

export default async function ProductsPage() {
  // Direct async/await - no useEffect needed
  const products = await getProducts()

  return (
    <main>
      <h1>Products</h1>
      <ul>
        {products.map((p) => (
          <li key={p.id}>{p.name}</li>
        ))}
      </ul>
    </main>
  )
}
```

### Client Components (Interactive)

```tsx
// components/features/product-filter.tsx
"use client"  // Required for interactivity

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

export function ProductFilter() {
  const [search, setSearch] = useState('')

  // Client-side data fetching with TanStack Query
  const { data, isPending } = useQuery({
    queryKey: ['products', search],
    queryFn: () => fetchProducts({ search }),
  })

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search..."
      />
      {isPending ? <p>Loading...</p> : <ProductList products={data} />}
    </div>
  )
}
```

---

## Layouts and Templates

### Root Layout (Required)

```tsx
// app/layout.tsx
import type { Metadata } from 'next'
import { Providers } from '@/components/providers'
import '@/app/globals.css'

export const metadata: Metadata = {
  title: 'Dataverse',
  description: 'Multi-vendor futures market data',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

### Nested Layout

```tsx
// app/(dashboard)/layout.tsx
import { Sidebar } from '@/components/sidebar'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}
```

---

## Data Fetching Patterns

### Server Component (Simple)

```tsx
// app/instruments/page.tsx
async function getInstruments() {
  const res = await fetch('http://localhost:3000/api/instruments', {
    next: { revalidate: 60 }, // ISR: revalidate every 60s
  })
  return res.json()
}

export default async function InstrumentsPage() {
  const instruments = await getInstruments()
  return <InstrumentTable data={instruments} />
}
```

### With TanStack Query (Client)

```tsx
// components/features/instruments-table.tsx
"use client"

import { useQuery } from '@tanstack/react-query'
import { getInstruments } from '@dataverse/sdk'

export function InstrumentsTable() {
  const { data, isPending, error } = useQuery({
    queryKey: ['instruments'],
    queryFn: () => getInstruments(),
  })

  if (isPending) return <TableSkeleton />
  if (error) return <ErrorMessage error={error} />

  return <DataTable columns={columns} data={data} />
}
```

---

## Server Actions (Forms)

### Basic Server Action

```tsx
// app/products/actions.ts
"use server"

import { revalidatePath } from 'next/cache'

export async function createProduct(formData: FormData) {
  const name = formData.get('name') as string

  await fetch('http://localhost:3000/api/products', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })

  revalidatePath('/products')
}
```

### With useActionState (React 19)

```tsx
// components/features/create-product-form.tsx
"use client"

import { useActionState } from 'react'
import { createProduct } from '@/app/products/actions'

export function CreateProductForm() {
  const [state, formAction, isPending] = useActionState(
    createProduct,
    { error: null }
  )

  return (
    <form action={formAction}>
      <input name="name" placeholder="Product name" required />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create'}
      </button>
      {state.error && <p className="text-red-500">{state.error}</p>}
    </form>
  )
}
```

---

## Route Handlers (API Routes)

```tsx
// app/api/health/route.ts
import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ status: 'ok', timestamp: new Date() })
}

// With request handling
export async function POST(request: Request) {
  const body = await request.json()

  // Process...

  return NextResponse.json({ success: true }, { status: 201 })
}
```

---

## Loading and Error States

### Loading UI (Suspense)

```tsx
// app/products/loading.tsx
export default function Loading() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4" />
      <div className="h-64 bg-gray-200 rounded" />
    </div>
  )
}
```

### Error Boundary

```tsx
// app/products/error.tsx
"use client"  // Error boundaries must be client components

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="p-4 bg-red-50 rounded">
      <h2>Something went wrong!</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```

---

## TanStack Query Provider Setup

```tsx
// components/providers.tsx
"use client"

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            gcTime: 5 * 60 * 1000, // 5 minutes (was cacheTime)
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

---

## Dynamic Route Segments

```tsx
// app/instruments/[symbol]/page.tsx
type Props = {
  params: Promise<{ symbol: string }>  // Next.js 15+ uses Promise
}

export default async function InstrumentPage({ params }: Props) {
  const { symbol } = await params
  const instrument = await getInstrument(symbol)

  return <InstrumentDetail data={instrument} />
}

// Generate static params for SSG
export async function generateStaticParams() {
  const instruments = await getInstruments()
  return instruments.map((i) => ({ symbol: i.symbol }))
}
```

---

## Key Reminders

1. **Server Components by default** - Only add `"use client"` when needed
2. **Use TanStack Query** for client-side data fetching, not raw `useEffect`
3. **Use `useActionState`** for form handling with Server Actions
4. **Params are now Promises** in Next.js 15+ - `await params`
5. **Turbopack is default** - Much faster dev server
6. **`gcTime` not `cacheTime`** in TanStack Query v5
7. **`isPending` not `isLoading`** in TanStack Query v5

---

## Resource Files

- [patterns.md](resources/patterns.md) - Advanced patterns: parallel routes, intercepting routes, streaming
- [anti-patterns.md](resources/anti-patterns.md) - Common mistakes to avoid
