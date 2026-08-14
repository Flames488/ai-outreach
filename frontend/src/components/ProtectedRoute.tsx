import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LoadingState } from "./States";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingState label="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
