import { Navigate } from "react-router-dom";

/**
 * @deprecated A página Gerencial foi descontinuada e consolidada diretamente no Dashboard.
 */
export function Gerencial() {
  return <Navigate to="/" replace />;
}

export default Gerencial;
