import React, { Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { Login } from "./pages/Login";

const Dashboard = React.lazy(() => import("./pages/Dashboard").then(m => ({ default: m.Dashboard })));
const Corridas = React.lazy(() => import("./pages/Corridas").then(m => ({ default: m.Corridas })));
const Motoboys = React.lazy(() => import("./pages/Motoboys").then(m => ({ default: m.Motoboys })));
const Empresas = React.lazy(() => import("./pages/Empresas").then(m => ({ default: m.Empresas })));
const Escala = React.lazy(() => import("./pages/Escala").then(m => ({ default: m.Escala })));
const Lancamentos = React.lazy(() => import("./pages/Lancamentos").then(m => ({ default: m.Lancamentos })));
const Financeiro = React.lazy(() => import("./pages/Financeiro").then(m => ({ default: m.Financeiro })));
const Relatorios = React.lazy(() => import("./pages/Relatorios").then(m => ({ default: m.Relatorios })));
const Snapshots = React.lazy(() => import("./pages/Snapshots").then(m => ({ default: m.Snapshots })));
const Sync = React.lazy(() => import("./pages/Sync").then(m => ({ default: m.Sync })));
const Usuarios = React.lazy(() => import("./pages/Usuarios").then(m => ({ default: m.Usuarios })));
const Configuracoes = React.lazy(() => import("./pages/Configuracoes").then(m => ({ default: m.Configuracoes })));
const Gerencial = React.lazy(() => import("./pages/Gerencial").then(m => ({ default: m.Gerencial })));
const Historico = React.lazy(() => import("./pages/Historico").then(m => ({ default: m.Historico })));

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { session, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="h-screen w-screen flex items-center justify-center bg-zinc-50"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div></div>;
  }
  
  if (!session) {
    return <Navigate to="/login" replace />;
  }
  
  return (
    <AppLayout>
      <Suspense fallback={<div className="h-full w-full flex items-center justify-center p-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div></div>}>
        {children}
      </Suspense>
    </AppLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          {/* Protected Routes */}
          <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/corridas" element={<PrivateRoute><Corridas /></PrivateRoute>} />
          <Route path="/motoboys" element={<PrivateRoute><Motoboys /></PrivateRoute>} />
          <Route path="/empresas" element={<PrivateRoute><Empresas /></PrivateRoute>} />
          <Route path="/escala" element={<PrivateRoute><Escala /></PrivateRoute>} />
          <Route path="/lancamentos" element={<PrivateRoute><Lancamentos /></PrivateRoute>} />
          <Route path="/financeiro" element={<PrivateRoute><Financeiro /></PrivateRoute>} />
          <Route path="/relatorios" element={<PrivateRoute><Relatorios /></PrivateRoute>} />
          <Route path="/snapshots" element={<PrivateRoute><Snapshots /></PrivateRoute>} />
          <Route path="/sync" element={<PrivateRoute><Sync /></PrivateRoute>} />
          <Route path="/usuarios" element={<PrivateRoute><Usuarios /></PrivateRoute>} />
          <Route path="/configuracoes" element={<PrivateRoute><Configuracoes /></PrivateRoute>} />
          <Route path="/gerencial" element={<PrivateRoute><Gerencial /></PrivateRoute>} />
          <Route path="/historico" element={<PrivateRoute><Historico /></PrivateRoute>} />
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
