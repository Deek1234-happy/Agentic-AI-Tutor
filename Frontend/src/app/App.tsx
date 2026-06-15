import { RouterProvider } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { router } from "./routes";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider } from "../context/AuthContext";
import { ThemeProvider } from "./components/theme-provider";

// Single QueryClient instance for the whole app.
// staleTime default of 0 means data is always considered stale after first fetch,
// but the cache still prevents duplicate in-flight requests.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,           // retry once on network errors
      staleTime: 0,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <RouterProvider router={router} />
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}