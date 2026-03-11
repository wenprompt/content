# TanStack Query Anti-Patterns

## Using isLoading instead of isPending (v5)

```tsx
// WRONG - isLoading renamed in v5
const { isLoading } = useQuery({ queryKey: ['data'], queryFn: fetchData })

// CORRECT - Use isPending
const { isPending } = useQuery({ queryKey: ['data'], queryFn: fetchData })

// Note: isLoading still exists but means isPending && !isFetched
```

## Using cacheTime instead of gcTime (v5)

```tsx
// WRONG - cacheTime renamed in v5
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { cacheTime: 5 * 60 * 1000 },
  },
})

// CORRECT - Use gcTime
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { gcTime: 5 * 60 * 1000 },
  },
})
```

## Missing HydrationBoundary for SSR

```tsx
// WRONG - Prefetched data not hydrated
export default async function Page() {
  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({ queryKey: ['data'], queryFn: getData })
  return <ClientComponent /> // Will refetch on client!
}

// CORRECT - Wrap with HydrationBoundary
import { dehydrate, HydrationBoundary } from '@tanstack/react-query'

export default async function Page() {
  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({ queryKey: ['data'], queryFn: getData })
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ClientComponent />
    </HydrationBoundary>
  )
}
```

## Mutating Query Data Directly

```tsx
// WRONG - Mutating cached data directly
const { data } = useQuery({ queryKey: ['products'], queryFn: getProducts })
data.push(newProduct) // Mutates cache directly!

// CORRECT - Use setQueryData with new reference
queryClient.setQueryData(['products'], (old) => [...old, newProduct])
```

## Missing queryKey Dependencies

```tsx
// WRONG - queryKey doesn't reflect dependencies
const { data } = useQuery({
  queryKey: ['products'],  // Same key regardless of filters!
  queryFn: () => getProducts({ search, category }),
})
// Won't refetch when search or category changes

// CORRECT - Include dependencies in queryKey
const { data } = useQuery({
  queryKey: ['products', { search, category }],
  queryFn: () => getProducts({ search, category }),
})
```

## Creating QueryClient in Render

```tsx
// WRONG - New client every render
function App() {
  const queryClient = new QueryClient() // Creates new instance each render!
  return <QueryClientProvider client={queryClient}>...</QueryClientProvider>
}

// CORRECT - Use useState or useMemo
function App() {
  const [queryClient] = useState(() => new QueryClient())
  return <QueryClientProvider client={queryClient}>...</QueryClientProvider>
}
```

## Using onSuccess/onError in useQuery (v5)

```tsx
// WRONG - Removed in v5
const { data } = useQuery({
  queryKey: ['products'],
  queryFn: getProducts,
  onSuccess: (data) => console.log('Loaded!'),  // Doesn't exist in v5!
})

// CORRECT - Use useEffect or handle in queryFn
const { data, isSuccess } = useQuery({
  queryKey: ['products'],
  queryFn: getProducts,
})

useEffect(() => {
  if (isSuccess) {
    console.log('Loaded!')
  }
}, [isSuccess])
```

## Forgetting to Invalidate After Mutations

```tsx
// WRONG - Cache becomes stale
const mutation = useMutation({
  mutationFn: updateProduct,
  onSuccess: () => {
    toast.success('Updated!')
    // Forgot to invalidate - list shows old data!
  },
})

// CORRECT - Always invalidate related queries
const mutation = useMutation({
  mutationFn: updateProduct,
  onSuccess: () => {
    toast.success('Updated!')
    queryClient.invalidateQueries({ queryKey: ['products'] })
  },
})
```

## Using useEffect for Data Fetching

```tsx
// WRONG - Manual state management
function Products() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    getProducts()
      .then(setProducts)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])
}

// CORRECT - Use TanStack Query
function Products() {
  const { data: products, isPending, error } = useQuery({
    queryKey: ['products'],
    queryFn: getProducts,
  })
}
```

## Not Using enabled for Conditional Queries

```tsx
// WRONG - Query runs even without userId
const { data } = useQuery({
  queryKey: ['user', userId],
  queryFn: () => getUser(userId!),  // Dangerous!
})

// CORRECT - Use enabled option
const { data } = useQuery({
  queryKey: ['user', userId],
  queryFn: () => getUser(userId!),
  enabled: !!userId,  // Only fetch when userId exists
})
```

## Too Aggressive Invalidation

```tsx
// WRONG - Invalidates everything on any mutation
const mutation = useMutation({
  mutationFn: updateProduct,
  onSuccess: () => {
    queryClient.invalidateQueries() // Invalidates ALL queries!
  },
})

// CORRECT - Targeted invalidation
const mutation = useMutation({
  mutationFn: updateProduct,
  onSuccess: (data, variables) => {
    queryClient.invalidateQueries({ queryKey: ['products', variables.id] })
    queryClient.invalidateQueries({ queryKey: ['products', 'list'] })
  },
})
```
