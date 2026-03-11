# TanStack Query Advanced Patterns

## Parallel Queries

```tsx
"use client"

import { useQueries } from '@tanstack/react-query'

export function Dashboard() {
  const results = useQueries({
    queries: [
      { queryKey: ['products'], queryFn: getProducts },
      { queryKey: ['orders'], queryFn: getOrders },
      { queryKey: ['stats'], queryFn: getStats },
    ],
  })

  const isLoading = results.some((r) => r.isPending)
  const [products, orders, stats] = results.map((r) => r.data)

  if (isLoading) return <DashboardSkeleton />

  return (
    <div>
      <ProductsWidget data={products} />
      <OrdersWidget data={orders} />
      <StatsWidget data={stats} />
    </div>
  )
}
```

## Dependent Queries

```tsx
export function UserPosts({ userId }: { userId: string }) {
  // First query
  const { data: user } = useQuery({
    queryKey: ['users', userId],
    queryFn: () => getUser(userId),
  })

  // Dependent query - only runs when user exists
  const { data: posts, isPending } = useQuery({
    queryKey: ['users', userId, 'posts'],
    queryFn: () => getUserPosts(userId),
    enabled: !!user,  // Only fetch when user is loaded
  })

  if (!user) return <UserSkeleton />
  if (isPending) return <PostsSkeleton />

  return <PostsList posts={posts} />
}
```

## Infinite Queries

```tsx
"use client"

import { useInfiniteQuery } from '@tanstack/react-query'

export function InfiniteProductList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['products', 'infinite'],
    queryFn: ({ pageParam }) => getProducts({ page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    maxPages: 5,  // v5: Limit memory usage
  })

  const products = data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div>
      <ul>
        {products.map((p) => (
          <li key={p.id}>{p.name}</li>
        ))}
      </ul>
      {hasNextPage && (
        <button
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  )
}
```

## Mutation with Rollback

```tsx
const deleteProductMutation = useMutation({
  mutationFn: deleteProduct,
  onMutate: async (productId) => {
    await queryClient.cancelQueries({ queryKey: ['products'] })

    const previousProducts = queryClient.getQueryData(['products'])

    // Optimistic removal
    queryClient.setQueryData(['products'], (old: Product[]) =>
      old.filter((p) => p.id !== productId)
    )

    return { previousProducts }
  },
  onError: (err, productId, context) => {
    // Rollback to previous state
    queryClient.setQueryData(['products'], context?.previousProducts)
    toast.error('Failed to delete product')
  },
  onSuccess: () => {
    toast.success('Product deleted')
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['products'] })
  },
})
```

## Polling / Auto-Refetch

```tsx
const { data } = useQuery({
  queryKey: ['job-status', jobId],
  queryFn: () => getJobStatus(jobId),
  refetchInterval: (query) => {
    // Stop polling when job is complete
    if (query.state.data?.status === 'completed') {
      return false
    }
    return 1000 // Poll every second
  },
})
```

## Prefetching on Hover

```tsx
export function ProductCard({ product }: { product: Product }) {
  const queryClient = useQueryClient()

  const handleMouseEnter = () => {
    // Prefetch details when hovering
    queryClient.prefetchQuery({
      queryKey: ['products', product.id],
      queryFn: () => getProductDetails(product.id),
      staleTime: 60 * 1000,
    })
  }

  return (
    <Link
      href={`/products/${product.id}`}
      onMouseEnter={handleMouseEnter}
    >
      {product.name}
    </Link>
  )
}
```

## Query with Select

```tsx
const { data: productNames } = useQuery({
  queryKey: ['products'],
  queryFn: getProducts,
  select: (data) => data.map((p) => p.name),  // Transform data
})

// productNames is string[] instead of Product[]
```

## Optimistic List Add

```tsx
const addProductMutation = useMutation({
  mutationFn: createProduct,
  onMutate: async (newProduct) => {
    await queryClient.cancelQueries({ queryKey: ['products'] })

    const previousProducts = queryClient.getQueryData(['products'])

    // Add optimistically with temp ID
    queryClient.setQueryData(['products'], (old: Product[]) => [
      ...old,
      { ...newProduct, id: 'temp-' + Date.now(), isOptimistic: true },
    ])

    return { previousProducts }
  },
  onError: (err, newProduct, context) => {
    queryClient.setQueryData(['products'], context?.previousProducts)
  },
  onSuccess: (data, variables) => {
    // Replace temp item with real item
    queryClient.setQueryData(['products'], (old: Product[]) =>
      old.map((p) => (p.isOptimistic ? data : p))
    )
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['products'] })
  },
})
```

## Retry with Exponential Backoff

```tsx
const { data } = useQuery({
  queryKey: ['flaky-api'],
  queryFn: flakyApiCall,
  retry: 3,
  retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
})
```

## Broadcast Across Tabs (Experimental)

```tsx
import { broadcastQueryClient } from '@tanstack/query-broadcast-client-experimental'

const queryClient = new QueryClient()

// Sync cache across browser tabs
broadcastQueryClient({
  queryClient,
  broadcastChannel: 'dataverse-app',
})
```
