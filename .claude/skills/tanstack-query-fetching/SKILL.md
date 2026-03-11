---
name: tanstack-query-fetching
description: TanStack Query v5 (React Query) data fetching with useQuery, useMutation, isPending (not isLoading), gcTime (not cacheTime), queryKey patterns, and HydrationBoundary for SSR. Use when implementing queries, invalidating cache, building optimistic mutations, or fixing stale data issues. Apply for .tsx files with @tanstack/react-query imports or QueryClientProvider. (project)
---

# TanStack Query Data Fetching

Modern patterns for TanStack Query v5 with React 19 (December 2025 best practices).

**Package Manager:** Use `pnpm` (`pnpm add @tanstack/react-query`).

## When To Apply

- Implementing client-side data fetching
- Setting up caching and invalidation
- Building mutations with optimistic updates
- Debugging stale data or refetch issues

## Quick Reference (v5 Changes)

| v4 | v5 | Notes |
|----|-----|-------|
| `isLoading` | `isPending` | Initial load state |
| `cacheTime` | `gcTime` | Garbage collection time |
| `useQuery({ suspense: true })` | `useSuspenseQuery()` | Dedicated hook |
| `onSuccess/onError` callbacks | Removed from useQuery | Use `useEffect` or mutation callbacks |

---

## Provider Setup

```tsx
// components/providers.tsx
"use client"

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  // Create client once per component instance
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,      // 1 minute
            gcTime: 5 * 60 * 1000,     // 5 minutes (was cacheTime)
            refetchOnWindowFocus: true,
            retry: 1,
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

## Basic Queries

### Simple Query

```tsx
"use client"

import { useQuery } from '@tanstack/react-query'
import { getInstruments } from '@dataverse/sdk'

export function InstrumentsList() {
  const { data, isPending, error } = useQuery({
    queryKey: ['instruments'],
    queryFn: () => getInstruments(),
  })

  if (isPending) return <Skeleton />
  if (error) return <ErrorMessage error={error} />

  return (
    <ul>
      {data?.map((inst) => (
        <li key={inst.id}>{inst.symbol}</li>
      ))}
    </ul>
  )
}
```

### Query with Parameters

```tsx
export function InstrumentDetail({ symbol }: { symbol: string }) {
  const { data, isPending } = useQuery({
    queryKey: ['instruments', symbol],  // Include params in key
    queryFn: () => getInstrument({ path: { symbol } }),
    enabled: !!symbol,  // Only fetch when symbol exists
  })

  // ...
}
```

### Query with Search/Filter

```tsx
export function FilteredProducts({ search, category }: FilterProps) {
  const { data, isPending } = useQuery({
    queryKey: ['products', { search, category }],  // Object in key
    queryFn: () => getProducts({ query: { search, category } }),
    placeholderData: (previousData) => previousData,  // Keep old data while loading
  })

  // ...
}
```

---

## Mutations

### Basic Mutation

```tsx
"use client"

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProduct } from '@dataverse/sdk'

export function CreateProductForm() {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      // Invalidate and refetch products list
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (error) => {
      console.error('Failed to create product:', error)
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    mutation.mutate({
      body: {
        name: formData.get('name') as string,
      },
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" required />
      <button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? 'Creating...' : 'Create'}
      </button>
      {mutation.error && <p className="text-red-500">{mutation.error.message}</p>}
    </form>
  )
}
```

### Optimistic Update

```tsx
const mutation = useMutation({
  mutationFn: updateProduct,
  onMutate: async (newProduct) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['products', newProduct.id] })

    // Snapshot previous value
    const previousProduct = queryClient.getQueryData(['products', newProduct.id])

    // Optimistically update
    queryClient.setQueryData(['products', newProduct.id], newProduct)

    // Return context for rollback
    return { previousProduct }
  },
  onError: (err, newProduct, context) => {
    // Rollback on error
    queryClient.setQueryData(['products', newProduct.id], context?.previousProduct)
  },
  onSettled: () => {
    // Always refetch after error or success
    queryClient.invalidateQueries({ queryKey: ['products'] })
  },
})
```

---

## Caching Strategies

### Stale Time vs GC Time

```tsx
const { data } = useQuery({
  queryKey: ['products'],
  queryFn: getProducts,
  staleTime: 5 * 60 * 1000,  // 5 min: data considered fresh
  gcTime: 30 * 60 * 1000,    // 30 min: keep in cache after unmount
})

// staleTime: How long before data is considered stale
//   - Fresh data: won't refetch on mount/focus/reconnect
//   - Stale data: will refetch in background

// gcTime: How long to keep unused data in cache
//   - After unmount, data stays in cache for gcTime
//   - Remounting uses cached data while refetching
```

### Invalidation Patterns

```tsx
const queryClient = useQueryClient()

// Invalidate exact query
queryClient.invalidateQueries({ queryKey: ['products', 123] })

// Invalidate all products queries
queryClient.invalidateQueries({ queryKey: ['products'] })

// Invalidate with predicate
queryClient.invalidateQueries({
  predicate: (query) =>
    query.queryKey[0] === 'products' &&
    (query.queryKey[1] as any)?.category === 'electronics',
})

// Remove from cache entirely
queryClient.removeQueries({ queryKey: ['products', 123] })
```

---

## SSR with Next.js

### Prefetch on Server

```tsx
// app/products/page.tsx
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { getProducts } from '@dataverse/sdk'
import { ProductsClient } from './products-client'

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

### Client Component Uses Prefetched Data

```tsx
// app/products/products-client.tsx
"use client"

import { useQuery } from '@tanstack/react-query'
import { getProducts } from '@dataverse/sdk'

export function ProductsClient() {
  // Uses prefetched data, no loading state on initial render
  const { data } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts(),
  })

  return <ProductTable data={data ?? []} />
}
```

---

## Suspense Mode

```tsx
"use client"

import { useSuspenseQuery } from '@tanstack/react-query'

export function ProductsList() {
  // No isPending - throws promise for Suspense
  const { data } = useSuspenseQuery({
    queryKey: ['products'],
    queryFn: getProducts,
  })

  return <ProductTable data={data} />
}

// Parent wraps with Suspense
export function ProductsPage() {
  return (
    <Suspense fallback={<Skeleton />}>
      <ProductsList />
    </Suspense>
  )
}
```

---

## Query Key Best Practices

```tsx
// Hierarchical keys for easy invalidation
const queryKey = ['products', productId, 'reviews']

// Object params for complex filters
const queryKey = ['products', { search, category, page }]

// Factory pattern for consistency
export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (filters: string) => [...productKeys.lists(), { filters }] as const,
  details: () => [...productKeys.all, 'detail'] as const,
  detail: (id: number) => [...productKeys.details(), id] as const,
}

// Usage
useQuery({ queryKey: productKeys.detail(123), queryFn: ... })
queryClient.invalidateQueries({ queryKey: productKeys.lists() })
```

---

## Error Handling

```tsx
// Global error handler
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error instanceof Error && error.message.includes('4')) {
          return false
        }
        return failureCount < 3
      },
    },
  },
})

// Per-query error handling
const { data, error, isError } = useQuery({
  queryKey: ['products'],
  queryFn: getProducts,
  throwOnError: false,  // Handle error in component
})

if (isError) {
  return <ErrorBoundary error={error} />
}
```

---

## Key Reminders

1. **`isPending` not `isLoading`** - Renamed in v5
2. **`gcTime` not `cacheTime`** - Renamed in v5
3. **Always use `queryKey` arrays** - First element is the "scope"
4. **Include params in `queryKey`** - For automatic refetch on change
5. **Use `HydrationBoundary`** for SSR prefetching
6. **Invalidate after mutations** - Don't rely on cache staleness
7. **Use `placeholderData`** for better UX during param changes

---

## Resource Files

- [patterns.md](resources/patterns.md) - Advanced: parallel queries, dependent queries
- [anti-patterns.md](resources/anti-patterns.md) - Common mistakes to avoid
