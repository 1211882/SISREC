import { Navigate, useLocation } from "react-router-dom";
import { getAuthUser } from "../utils/api";

function ProtectedRoute({ children }) {
  const authUser = getAuthUser();
  const location = useLocation();

  if (!authUser?.id || !authUser?.access_token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export default ProtectedRoute;
