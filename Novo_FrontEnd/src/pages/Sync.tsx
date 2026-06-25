import { useState } from "react";
import { Activity, Webhook, RefreshCcw, WifiOff, LayoutDashboard, Key, Clock, ShieldCheck, GitPullRequest, Settings, Link2 } from "lucide-react";
import { cn } from "../lib/utils";

export function Sync() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-2">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight flex items-center gap-2">
            Central de Sincronização & API
          </h1>
          <p className="text-[13px] font-medium text-zinc-500 mt-1 max-w-2xl">
            Gateway de integração, webhooks, proxy de despacho (Nola), e monitoramento de cron jobs e filas em tempo real.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-emerald-700 bg-emerald-50/50 px-2.5 py-1.5 rounded-md border border-emerald-200/60 shadow-sm">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
            Conexão Estável
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Webhooks & Eventos */}
        <div className="glass-panel p-0 overflow-hidden flex flex-col">
          <div className="p-5 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
             <div className="flex items-center gap-3">
               <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg border border-indigo-100">
                 <Webhook strokeWidth={2} className="w-5 h-5" />
               </div>
               <div>
                 <h2 className="text-sm font-bold text-zinc-900">Escuta de Eventos (Webhooks)</h2>
                 <p className="text-[11px] font-medium text-zinc-500">Atualizações de status em tempo real</p>
               </div>
             </div>
             <div className="flex items-center gap-2">
               <span className="text-[10px] font-mono text-zinc-500">142 eventos/min</span>
               <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
             </div>
          </div>
          <div className="p-5 space-y-4">
             <div className="bg-zinc-900 text-zinc-300 p-4 rounded-lg font-mono text-[11px] overflow-x-auto shadow-inner border border-zinc-800">
               <div className="text-zinc-500 mb-2">// Último Payload Recebido (Validação HMAC OK)</div>
               <span className="text-emerald-400">POST</span> /api/webhooks/taxi-machine/status
               <br/>
               <span className="text-zinc-500">{"{"}</span>
               <br/>
               &nbsp;&nbsp;<span className="text-blue-300">"event"</span>: <span className="text-amber-300">"ride.status_updated"</span>,
               <br/>
               &nbsp;&nbsp;<span className="text-blue-300">"ride_id"</span>: <span className="text-amber-300">"1459203"</span>,
               <br/>
               &nbsp;&nbsp;<span className="text-blue-300">"status"</span>: <span className="text-amber-300">"COMPLETED"</span>
               <br/>
               <span className="text-zinc-500">{"}"}</span>
             </div>
             
             <div className="flex justify-between items-center text-[12px] font-medium border border-zinc-100 rounded-lg p-3 bg-zinc-50">
                <span className="flex items-center gap-2 text-zinc-700">
                  <ShieldCheck strokeWidth={2} className="w-4 h-4 text-emerald-500" />
                  Assinatura Digital de Webhooks
                </span>
                <span className="text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">Ativado</span>
             </div>
          </div>
        </div>

        {/* Proxy Gateway (Nola) */}
        <div className="glass-panel p-0 overflow-hidden flex flex-col">
          <div className="p-5 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
             <div className="flex items-center gap-3">
               <div className="p-2 bg-blue-50 text-blue-600 rounded-lg border border-blue-100">
                 <GitPullRequest strokeWidth={2} className="w-5 h-5" />
               </div>
               <div>
                 <h2 className="text-sm font-bold text-zinc-900">API Gateway (Nola)</h2>
                 <p className="text-[11px] font-medium text-zinc-500">Ponte para parceiros enviarem pedidos</p>
               </div>
             </div>
          </div>
          <div className="p-5 space-y-4">
             <p className="text-[13px] text-zinc-600 leading-relaxed">
               Permite que sistemas parceiros despachem pedidos usando uma API simplificada. 
               O backend traduz e injeta as credenciais de frota master automaticamente, mantendo a segurança (API Proxy).
             </p>
             <div className="space-y-3">
               <div className="flex justify-between items-center text-sm p-3 border border-zinc-200 rounded-lg">
                 <div className="flex items-center gap-3">
                   <Key className="w-4 h-4 text-zinc-400" />
                   <div>
                     <p className="font-semibold text-zinc-900">Chave de Ingress (Parceiro A)</p>
                     <p className="text-[11px] text-zinc-500">sk_live_nx3...8f9a</p>
                   </div>
                 </div>
                 <button className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 hover:text-zinc-900 transition-colors">Revogar</button>
               </div>
             </div>
             <button className="w-full py-2 bg-white border border-zinc-200 shadow-sm rounded-lg text-[12px] font-bold text-zinc-700 hover:bg-zinc-50 transition-colors">
               Gerar Nova Chave de Acesso
             </button>
          </div>
        </div>

        {/* Automações Cron */}
        <div className="glass-panel p-0 overflow-hidden flex flex-col lg:col-span-2">
          <div className="p-5 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
             <div className="flex items-center gap-3">
               <div className="p-2 bg-amber-50 text-amber-600 rounded-lg border border-amber-100">
                 <RefreshCcw strokeWidth={2} className="w-5 h-5" />
               </div>
               <div>
                 <h2 className="text-sm font-bold text-zinc-900">Rotinas de Automação de Fundo (Cron Jobs)</h2>
                 <p className="text-[11px] font-medium text-zinc-500">Processos assíncronos e retentativas (Retry Queues)</p>
               </div>
             </div>
          </div>
          <div className="p-0 overflow-x-auto">
             <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-zinc-50/30 border-b border-zinc-100">
                    <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Rotina</th>
                    <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Frequência</th>
                    <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Última Execução</th>
                    <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="text-sm divide-y divide-zinc-100">
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-zinc-900 text-[13px]">Limpeza de Faltas (Auto No-Show)</p>
                      <p className="text-[11px] text-zinc-500 mt-0.5">Marca ausência para motoristas confirmados que não compareceram ao turno.</p>
                    </td>
                    <td className="px-5 py-3.5 text-[12px] font-mono text-zinc-600">A cada 15 min</td>
                    <td className="px-5 py-3.5 text-[12px] font-medium text-zinc-600">Hoje, 10:15</td>
                    <td className="px-5 py-3.5 text-center">
                      <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]"></span>
                    </td>
                  </tr>
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-zinc-900 text-[13px]">Auto-Vinculação de Motoristas</p>
                      <p className="text-[11px] text-zinc-500 mt-0.5">Detecta corridas de novos motoristas no despacho e os cadastra localmente.</p>
                    </td>
                    <td className="px-5 py-3.5 text-[12px] font-mono text-zinc-600">Event-driven / 5 min</td>
                    <td className="px-5 py-3.5 text-[12px] font-medium text-zinc-600">Hoje, 10:20</td>
                    <td className="px-5 py-3.5 text-center">
                      <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]"></span>
                    </td>
                  </tr>
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-zinc-900 text-[13px]">Fila de Créditos e Retentativas</p>
                      <p className="text-[11px] text-zinc-500 mt-0.5">Processa créditos que falharam na API (Rate Limit/Instabilidade) via Exponential Backoff.</p>
                    </td>
                    <td className="px-5 py-3.5 text-[12px] font-mono text-zinc-600">Contínuo</td>
                    <td className="px-5 py-3.5 text-[12px] font-medium text-zinc-600">Em andamento (2 na fila)</td>
                    <td className="px-5 py-3.5 text-center">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-600 border border-amber-200">Processing</span>
                    </td>
                  </tr>
                </tbody>
             </table>
          </div>
        </div>

      </div>
    </div>
  );
}
