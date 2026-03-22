import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider, keepPreviousData } from '@tanstack/react-query'
import { AuthProvider } from '@/context/AuthContext'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,          // dado fresco por 30s (sem refetch)
      gcTime: 5 * 60_000,         // mantém cache 5min após componente desmontar
      refetchOnWindowFocus: false, // sem refetch ao alt+tab — API decide via Cache-Control
      placeholderData: keepPreviousData, // mantém dado anterior enquanto refetch roda (sem flicker)
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
