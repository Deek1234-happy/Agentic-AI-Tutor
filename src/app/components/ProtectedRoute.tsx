/**
 * ProtectedRoute — redirects unauthenticated users to "/" (Welcome page).
 * Wrap any route element with this component to require a valid session.
 */

import { Navigate, Outlet } from "react-router";
import { useAuth } from "../../context/AuthContext";

export default function ProtectedRoute() {
  const { session } = useAuth();

  if (!session) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
