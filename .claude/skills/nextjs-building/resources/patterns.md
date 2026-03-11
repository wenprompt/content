# Next.js Advanced Patterns

## Parallel Routes

Display multiple pages simultaneously in the same layout:

```
app/
├── @modal/
│   └── (.)products/[id]/
│       └── page.tsx    # Intercepted modal
├── @sidebar/
│   └── default.tsx
└── layout.tsx          # Receives both as props
```

```tsx
// app/layout.tsx
export default function Layout({
  children,
  modal,
  sidebar,
}: {
  children: React.ReactNode
  modal: React.ReactNode
  sidebar: React.ReactNode
}) {
  return (
    <div className="flex">
      {sidebar}
      <main>{children}</main>
      {modal}
    </div>
  )
}
```

## Intercepting Routes

Show modal on soft navigation, full page on hard navigation:

```tsx
// app/@modal/(.)products/[id]/page.tsx
import { Modal } from '@/components/ui/modal'

export default async function ProductModal({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const product = await getProduct(id)

  return (
    <Modal>
      <ProductDetails product={product} />
    </Modal>
  )
}
```

## Streaming with Suspense

```tsx
// app/dashboard/page.tsx
import { Suspense } from 'react'

export default function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>

      {/* Streams independently */}
      <Suspense fallback={<ChartSkeleton />}>
        <SlowChart />
      </Suspense>

      <Suspense fallback={<TableSkeleton />}>
        <SlowTable />
      </Suspense>
    </div>
  )
}

// Each component fetches its own data
async function SlowChart() {
  const data = await getChartData() // 2s
  return <Chart data={data} />
}

async function SlowTable() {
  const data = await getTableData() // 3s
  return <DataTable data={data} />
}
```

## Optimistic Updates

```tsx
"use client"

import { useOptimistic } from 'react'
import { updateProduct } from '@/app/products/actions'

export function ProductList({ products }) {
  const [optimisticProducts, addOptimisticProduct] = useOptimistic(
    products,
    (state, newProduct) => [...state, { ...newProduct, pending: true }]
  )

  async function handleCreate(formData: FormData) {
    const newProduct = { name: formData.get('name') as string }
    addOptimisticProduct(newProduct) // Immediate UI update
    await updateProduct(formData) // Server action
  }

  return (
    <form action={handleCreate}>
      {/* ... */}
    </form>
  )
}
```

## Route Segment Config

```tsx
// app/products/page.tsx

// Force dynamic rendering (SSR)
export const dynamic = 'force-dynamic'

// Or force static (SSG)
export const dynamic = 'force-static'

// ISR with revalidation
export const revalidate = 60 // seconds

// Runtime
export const runtime = 'nodejs' // or 'edge'
```

## Middleware

```tsx
// middleware.ts (project root)
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Auth check
  const token = request.cookies.get('auth-token')

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/api/:path*'],
}
```

## Prefetching with TanStack Query

```tsx
// app/products/page.tsx
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { getProducts } from '@dataverse/sdk'

export default async function ProductsPage() {
  const queryClient = new QueryClient()

  // Prefetch on server
  await queryClient.prefetchQuery({
    queryKey: ['products'],
    queryFn: () => getProducts(),
  })

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ProductsClient />
    </HydrationBoundary>
  )
}
```

## Search Params with nuqs

```tsx
// app/products/page.tsx
"use client"

import { useQueryState, parseAsString, parseAsInteger } from 'nuqs'

export function ProductFilters() {
  // Type-safe URL state
  const [search, setSearch] = useQueryState('q', parseAsString.withDefault(''))
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1))

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <Pagination page={page} onChange={setPage} />
    </div>
  )
}
```
