# Next.js Anti-Patterns

## Using "use client" Unnecessarily

```tsx
// WRONG - Making everything a client component
"use client"

export default function ProductList({ products }) {
  return (
    <ul>
      {products.map((p) => <li key={p.id}>{p.name}</li>)}
    </ul>
  )
}

// CORRECT - Server component by default (no interactivity needed)
export default function ProductList({ products }) {
  return (
    <ul>
      {products.map((p) => <li key={p.id}>{p.name}</li>)}
    </ul>
  )
}
```

## Using useEffect for Data Fetching

```tsx
// WRONG - Client-side fetching with useEffect
"use client"

export function Products() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    fetch('/api/products')
      .then((r) => r.json())
      .then(setProducts)
  }, [])

  return <ProductList products={products} />
}

// CORRECT - Server Component or TanStack Query
// Option 1: Server Component
export default async function Products() {
  const products = await getProducts()
  return <ProductList products={products} />
}

// Option 2: TanStack Query for client-side
"use client"
export function Products() {
  const { data } = useQuery({
    queryKey: ['products'],
    queryFn: getProducts,
  })
  return <ProductList products={data ?? []} />
}
```

## Not Awaiting params in Next.js 15+

```tsx
// WRONG - Params are now Promises
export default function Page({ params }: { params: { id: string } }) {
  const product = await getProduct(params.id) // Type error!
}

// CORRECT - Await params
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const product = await getProduct(id)
}
```

## Using isLoading instead of isPending (TanStack Query v5)

```tsx
// WRONG - isLoading renamed to isPending
const { isLoading } = useQuery({ queryKey: ['data'], queryFn: fetch })

// CORRECT - Use isPending
const { isPending } = useQuery({ queryKey: ['data'], queryFn: fetch })
```

## Using cacheTime instead of gcTime

```tsx
// WRONG - cacheTime renamed to gcTime
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      cacheTime: 5 * 60 * 1000, // Deprecated!
    },
  },
})

// CORRECT - Use gcTime
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 5 * 60 * 1000,
    },
  },
})
```

## Forgetting HydrationBoundary for SSR

```tsx
// WRONG - Data not hydrated on client
export default async function Page() {
  const queryClient = new QueryClient()
  await queryClient.prefetchQuery({ queryKey: ['data'], queryFn: getData })

  return <ClientComponent /> // Client refetches!
}

// CORRECT - Hydrate prefetched data
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

## Massive Client Components

```tsx
// WRONG - Entire page is client component
"use client"

export default function DashboardPage() {
  const [filter, setFilter] = useState('')
  // ... lots of non-interactive rendering

  return (
    <div>
      <input value={filter} onChange={(e) => setFilter(e.target.value)} />
      {/* Static content that could be server-rendered */}
      <StaticHeader />
      <StaticSidebar />
      <FilteredContent filter={filter} />
    </div>
  )
}

// CORRECT - Island architecture
// app/dashboard/page.tsx (Server Component)
export default function DashboardPage() {
  return (
    <div>
      <FilterInput /> {/* Client Component */}
      <StaticHeader /> {/* Server Component */}
      <StaticSidebar /> {/* Server Component */}
      <DashboardContent /> {/* Server Component with client island */}
    </div>
  )
}
```

## Not Using loading.tsx

```tsx
// WRONG - Manual loading states everywhere
export default async function Page() {
  const data = await slowFetch() // User sees blank page
  return <Content data={data} />
}

// CORRECT - Add loading.tsx for automatic Suspense
// app/page.tsx
export default async function Page() {
  const data = await slowFetch()
  return <Content data={data} />
}

// app/loading.tsx
export default function Loading() {
  return <Skeleton />
}
```

## Direct API Calls Instead of Server Actions

```tsx
// WRONG - Exposing internal API
"use client"

async function handleSubmit(data: FormData) {
  await fetch('/api/internal/products', { method: 'POST', body: data })
}

// CORRECT - Use Server Actions
// actions.ts
"use server"

export async function createProduct(formData: FormData) {
  // Direct database access, no API route needed
  await db.insert(products).values({...})
  revalidatePath('/products')
}

// component.tsx
"use client"
import { createProduct } from './actions'

function Form() {
  return <form action={createProduct}>...</form>
}
```
