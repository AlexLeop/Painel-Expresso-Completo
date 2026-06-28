import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import type { ReactNode } from "react";
import {
  Search,
  Filter,
  MapPin,
  Navigation,
  Clock,
  Truck,
  Phone,
  MessageSquare,
  ShieldCheck,
  Mail,
  Map as MapIcon,
  ChevronRight,
  Store,
  FileDown,
  Plus,
  User,
  Loader2,
  Ban,
  ExternalLink,
  Layers,
  FileText,
} from "lucide-react";
import { formatCurrency, cn } from "../lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import {
  MapContainer,
  TileLayer,
  Marker,
  useMap,
  Popup,
  Tooltip,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { RideMapModal } from "../components/maps/RideMapModal";
import { CreateRideModal } from "../components/CreateRideModal";
import { PainelLobby } from "../components/PainelLobby";
import { FilaDinamica } from "../components/FilaDinamica";
import { RideChatModal } from "../components/RideChatModal";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { supabase } from "../lib/supabase";
import { ErrorBoundary } from "../components/ErrorBoundary";

export interface RideData {
  id: number;
  status: string;
  motoboy?: string | Record<string, any>;
  empresa?: string | Record<string, any>;
  amount?: number;
  created_at: string;
  updated_at: string;
  [key: string]: any;
}

// Fix Leaflet default icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const dropoffIcon = L.divIcon({
  html: `
    <div title="Entrega" style="width: 34px; height: 34px; border-radius: 12px; background: #10b981; border: 2px solid #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.18); display: flex; align-items: center; justify-content: center;">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#064e3b" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 21s7-4.35 7-11a7 7 0 0 0-14 0c0 6.65 7 11 7 11Z"/>
        <circle cx="12" cy="10" r="2.5"/>
      </svg>
    </div>
  `,
  className: "",
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

const storeIcon = L.divIcon({
  html: `<div style="background-color: #2563eb; padding: 8px; border-radius: 9999px; border: 2px solid white; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1); color: white; display: flex; align-items: center; justify-content: center;">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M3 9 4 3h16l1 6" />
      <path d="M4 9h16" />
      <path d="M5 9v12h14V9" />
      <path d="M9 21v-6h6v6" />
    </svg>
  </div>`,
  className: "",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const driverIcon = L.divIcon({
  html: `<div style="background-color: #09090b; padding: 8px; border-radius: 9999px; border: 2px solid #10b981; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1); color: #10b981; display: flex; align-items: center; justify-content: center; transform: rotate(-45deg);">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
  </div>`,
  className: "",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const driverIconSelected = L.divIcon({
  html: `<div style="background-color: #09090b; padding: 8px; border-radius: 9999px; border: 3px solid #f59e0b; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.18); color: #10b981; display: flex; align-items: center; justify-content: center; transform: rotate(-45deg);">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
  </div>`,
  className: "",
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

const selfIcon = L.divIcon({
  html: `<div title="Sua localização" style="width: 34px; height: 34px; border-radius: 9999px; background: #2563eb; border: 3px solid #ffffff; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.18); display: flex; align-items: center; justify-content: center;">
    <div style="width: 10px; height: 10px; border-radius: 9999px; background: #ffffff;"></div>
  </div>`,
  className: "",
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

// Map Controller to handle camera movements
function MapController({
  coords,
  rideId,
  focusKey,
}: {
  coords: [number, number] | null;
  rideId: string | number | undefined;
  focusKey?: number;
}) {
  const map = useMap();
  const lastRideId = useRef<string | number | undefined>(undefined);
  const lastFocusKey = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!coords) return;
    // Trigger flyTo when ride changes OR focusKey changes (driver click)
    if (
      rideId !== lastRideId.current ||
      (focusKey !== undefined && focusKey !== lastFocusKey.current)
    ) {
      map.flyTo(coords, 15, { duration: 1.5 });
      lastRideId.current = rideId;
      lastFocusKey.current = focusKey;
    }
  }, [coords, rideId, focusKey, map]);
  return null;
}

type DriverPosition = {
  machine_condutor_id: string;
  latitude: number;
  longitude: number;
  speed?: number;
  heading?: number;
  machine_ride_id?: string | null;
  received_at: string;
};

function parseCoordNumber(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  const raw = String(v ?? "").trim();
  if (!raw) return null;
  const normalized = raw.replace(",", ".");
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

function normalizeLatLng(
  latRaw: unknown,
  lngRaw: unknown,
): { lat: number; lng: number } | null {
  let lat = parseCoordNumber(latRaw);
  let lng = parseCoordNumber(lngRaw);
  if (lat === null || lng === null) return null;

  const inRange = (a: number, b: number) =>
    Math.abs(a) <= 90 && Math.abs(b) <= 180;
  if (inRange(lat, lng)) return { lat, lng };

  if (inRange(lng, lat)) return { lat: lng, lng: lat };

  const scales = [1e7, 1e6, 1e5];
  for (const s of scales) {
    const slat = lat / s;
    const slng = lng / s;
    if (inRange(slat, slng)) return { lat: slat, lng: slng };
    if (inRange(slng, slat)) return { lat: slng, lng: slat };
  }

  return null;
}

function haversineKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const R = 6371;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const s =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
  return R * c;
}

export function Corridas() {
  const [viewMode, setViewMode] = useState<"map" | "history">("map");
  const [selectedCorrida, setSelectedCorrida] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState("Informações do motorista");
  const [leftPanelMode, setLeftPanelMode] = useState<
    "lobby" | "fila" | "machine"
  >("lobby");
  const [selectedHistoryMap, setSelectedHistoryMap] = useState<any | null>(
    null,
  );
  const [activeSubTab, setActiveSubTab] = useState<"aguardando" | "despachado">(
    "aguardando",
  );

  const [activeRides, setActiveRides] = useState<any[]>([]);
  const [historyRides, setHistoryRides] = useState<any[]>([]);
  const [companies, setCompanies] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [redistributeRideData, setRedistributeRideData] = useState<any>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [historyFilter, setHistoryFilter] = useState("Todas");
  const [activeSearch, setActiveSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("Todos");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const [driverPositions, setDriverPositions] = useState<DriverPosition[]>([]);
  const [storeLocation, setStoreLocation] = useState<[number, number] | null>(
    null,
  );
  const [machineCompanyData, setMachineCompanyData] = useState<any | null>(
    null,
  );
  const [historyHeight, setHistoryHeight] = useState(350); // Altura inicial
  const isResizing = useRef(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loadingTracking, setLoadingTracking] = useState<string | null>(null);
  const [focusDriverId, setFocusDriverId] = useState<string | null>(null);
  const [focusKey, setFocusKey] = useState(0);

  const { session, globalSearch } = useAuth();
  const knownDriverIdsRef = useRef<Set<string>>(new Set());
  const activeDriverIdsRef = useRef<Set<string>>(new Set());
  const companyDriverIdsRef = useRef<Set<string>>(new Set());
  const [driverDirectory, setDriverDirectory] = useState<
    Record<string, { name: string; phone: string; status: string }>
  >({});

  useEffect(() => {
    companyDriverIdsRef.current = new Set(Object.keys(driverDirectory));
  }, [driverDirectory]);
  const mapDebug = useMemo(() => {
    try {
      return localStorage.getItem("nevesgo:mapDebug") === "1";
    } catch {
      return false;
    }
  }, []);
  const [selfPosition, setSelfPosition] = useState<[number, number] | null>(
    null,
  );

  useEffect(() => {
    const ids = new Set<string>();
    for (const r of activeRides) {
      const id = String(r?.motoboy?.id_num || "");
      if (id) ids.add(id);
    }
    activeDriverIdsRef.current = ids;
  }, [activeRides]);

  useEffect(() => {
    if (viewMode !== "map") return;
    if (!("geolocation" in navigator)) return;

    let watchId: number | null = null;
    try {
      watchId = navigator.geolocation.watchPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          if (Number.isFinite(lat) && Number.isFinite(lng)) {
            setSelfPosition([lat, lng]);
          }
        },
        () => {
          setSelfPosition(null);
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 },
      );
    } catch {
      setSelfPosition(null);
    }

    return () => {
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    };
  }, [viewMode]);

  useEffect(() => {
    setCurrentPage(1);
  }, [historySearch, historyFilter, activeSearch, activeFilter, globalSearch]);
  const user = session?.user as any;
  const companyId = user?.machine_empresa_id;

  // Identificação robusta da empresa logada
  const currentCompany = useMemo(() => {
    const found = user?.companies?.find(
      (c: any) => String(c.id) === String(companyId),
    );
    if (found) return found;
    if (user?.companies?.length === 1) return user.companies[0];
    return null;
  }, [user, companyId]);

  const companyName = currentCompany?.nome || user?.name || "Empresa";

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const posByDriverId = useMemo(() => {
    const map = new Map<string, DriverPosition>();
    for (const p of driverPositions) {
      const id = String(p.machine_condutor_id);
      const prev = map.get(id);
      if (!prev) {
        map.set(id, p);
      } else {
        const prevT = new Date(prev.received_at).getTime();
        const nextT = new Date(p.received_at).getTime();
        map.set(id, Number.isFinite(nextT) && nextT >= prevT ? p : prev);
      }
    }
    return map;
  }, [driverPositions]);

  const onlineCount = posByDriverId.size;
  const selectedDriverId = String(selectedCorrida?.motoboy?.id_num || "");
  const selfToPickupKm = useMemo(() => {
    if (!selfPosition) return null;
    if (!selectedCorrida?.origin) return null;
    const km = haversineKm(
      { lat: selfPosition[0], lng: selfPosition[1] },
      { lat: selectedCorrida.origin.lat, lng: selectedCorrida.origin.lng },
    );
    if (!Number.isFinite(km)) return null;
    return km;
  }, [selfPosition, selectedCorrida]);

  useEffect(() => {
    if (!mapDebug) return;
    console.debug("[Mapa] onlineCount/markers:", {
      onlineCount,
      markers: posByDriverId.size,
      activeRides: activeRides.length,
      selectedDriverId: selectedDriverId || null,
    });
  }, [
    mapDebug,
    onlineCount,
    posByDriverId,
    activeRides.length,
    selectedDriverId,
  ]);

  const handleOpenTracking = async (idMch: string | number) => {
    setLoadingTracking(String(idMch));
    try {
      const res = await authFetch(
        `/api/machine/rides/tracking?id_mch=${idMch}`,
      );
      const data = await res.json();
      if (
        res.ok &&
        (data.response?.[0]?.link_rastreio || data.links?.[0]?.link_rastreio)
      ) {
        const url =
          data.response?.[0]?.link_rastreio || data.links?.[0]?.link_rastreio;
        window.open(url, "_blank", "noopener,noreferrer");
        showToast("Abrindo link de rastreio ao vivo em nova aba");
      } else {
        const errorMsg =
          data?.details?.errors?.[0]?.message ||
          data?.error ||
          "Link não disponível para esta corrida";
        showToast(`Rastreio: ${errorMsg}`);
      }
    } catch {
      showToast("Erro ao obter link de rastreio");
    } finally {
      setLoadingTracking(null);
    }
  };

  useEffect(() => {
    const fetchDados = async (silent = false) => {
      if (!companyId) return;
      try {
        if (!silent) setLoading(true);

        // Fetch companies first if not already loaded to map IDs to names
        let currentCompanies = companies;
        if (Object.keys(companies).length === 0) {
          try {
            const compRes = await authFetch("/api/machine/companies");
            if (compRes.ok) {
              const compData = await compRes.json();
              const map: Record<string, string> = {};
              compData.companies?.forEach((c: any) => {
                map[String(c.id)] = c.nome;
              });
              setCompanies(map);
              currentCompanies = map;
            }
          } catch (err) {
            logger.error("Erro ao buscar lista de empresas:", err);
          }
        }

        // Always reset selectedCorrida when fetching (company may have changed)
        if (!silent) setSelectedCorrida(null);

        // Use the correct backend route that filters by company and uses Machine API
        const params = new URLSearchParams({ limite: "1000" });
        if (companyId) params.set("empresa_id", String(companyId));

        const res = await authFetch(`/api/machine/rides?${params.toString()}`);

        if (res.ok) {
          const data = await res.json();
          // Backend returns { rides: RideData[], total: number }
          const rawRides: any[] = data.rides || [];

          // Map Machine API fields → component fields
          const STATUS_ATIVO = new Set(["D", "G", "P", "A", "E", "S"]);
          const STATUS_LABEL: Record<string, string> = {
            D: "Aguardando",
            G: "Aguardando",
            P: "Aguardando",
            A: "Aceita",
            E: "Em andamento",
            S: "A caminho",
            F: "Concluída",
            C: "Cancelada",
            N: "Não atendida",
          };

          const mapRide = (r: any) => {
            const rideEmpresaId = String(r.empresa_id);
            const rideEmpresaNome =
              currentCompanies[rideEmpresaId] ||
              r.nome_empresa ||
              rideEmpresaId ||
              "Empresa";

            const p0 = r.paradas?.[0] || {};
            let rawCode =
              r.identificador_solicitacao ||
              r.identificador ||
              r.codigo_pedido ||
              r.numero_pedido ||
              r.pedido_id ||
              p0.codigo_pedido ||
              p0.id_pedido ||
              p0.numero_pedido ||
              "";
            if (
              String(rawCode).trim() === "0001" ||
              String(rawCode).trim() === "1" ||
              !rawCode
            ) {
              const obs = [
                r.observacao,
                r.observacoes,
                r.dados_extras,
                p0.observacao_parada,
                p0.observacao,
              ]
                .filter(Boolean)
                .join(" ");
              const m = obs.match(
                /(?:pedido|ped|order|id|código)[\s:#-]+(\d{2,15})/i,
              );
              if (m && m[1]) {
                rawCode = m[1];
              }
            }
            const codigoPedido = String(rawCode || "0001").trim();

            // Use backend-enriched client name (primary). DO NOT use nome_passageiro — it's the store/company name.
            let clienteNome =
              r.cliente_nome || p0.nome_contato || p0.nome_cliente || "";

            if (!clienteNome || String(clienteNome).trim() === "") {
              const obsText = [
                p0.observacao_parada,
                p0.observacao,
                r.observacao,
                r.observacoes,
                r.dados_extras,
                p0.complemento,
              ]
                .filter(Boolean)
                .join(" ");
              const match = obsText.match(
                /(?:cliente|contato|para|nome|sr|sra|recebedor|a\/c)[:\s-]+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,35})/i,
              );
              if (match && match[1]) {
                clienteNome = match[1].trim();
              } else {
                clienteNome = "Cliente Final";
              }
            }

            const telefoneCliente =
              r.cliente_telefone ||
              p0.telefone_contato ||
              p0.telefone_cliente ||
              p0.telefone_cliente_parada ||
              p0.telefone ||
              r.telefone_passageiro ||
              r.telefone_destino ||
              "";

            const stopCount = Array.isArray(r.paradas) ? r.paradas.length : 0;
            const tipoPedido =
              stopCount > 1
                ? "Multi-entrega"
                : r.com_retorno
                  ? "Com retorno"
                  : "Simples";

            return {
              id: r.id,
              codigoPedido,
              status:
                STATUS_LABEL[r.status_solicitacao] ||
                r.status_solicitacao ||
                "Desconhecido",
              rawStatus: r.status_solicitacao,
              tipo: tipoPedido,
              horario: r.data_hora_solicitacao
                ? r.data_hora_solicitacao.split(" ")[1]
                : "",
              data: r.data_hora_solicitacao
                ? r.data_hora_solicitacao
                    .split(" ")[0]
                    .split("-")
                    .reverse()
                    .join("/")
                : "",
              cliente: clienteNome,
              telefoneCliente,
              empresa: rideEmpresaNome,
              distancia: r.distancia_percorrida_km
                ? `${parseFloat(r.distancia_percorrida_km).toFixed(1)} km`
                : "—",
              valor: parseFloat(r.valor_corrida || "0"),
              telefoneMotorista:
                r.telefone_condutor || r.telefone_taxista || "",
              motoboy: {
                nome: r.nome_condutor || r.nome_taxista || "Sem motorista",
                placa: r.placa_veiculo || "",
                veiculo: r.veiculo || "",
                cnh: "",
                id_num: r.condutor_id || "",
                exp: "",
              },
              coleta: {
                endereco: r.coleta?.endereco || "",
                hora: r.data_hora_solicitacao
                  ? r.data_hora_solicitacao.split(" ")[1].substring(0, 5)
                  : "--:--",
              },
              entrega: {
                endereco: r.paradas?.[0]?.endereco || "",
                hora: r.data_hora_finalizacao
                  ? r.data_hora_finalizacao.split(" ")[1].substring(0, 5)
                  : "--:--",
              },
              origin:
                (r.coleta?.latitude ?? r.coleta?.lat) &&
                (r.coleta?.longitude ?? r.coleta?.lng)
                  ? {
                      lat: parseFloat(
                        String(r.coleta.latitude ?? r.coleta.lat),
                      ),
                      lng: parseFloat(
                        String(r.coleta.longitude ?? r.coleta.lng),
                      ),
                    }
                  : null,
              destination:
                (r.paradas?.[0]?.latitude ?? r.paradas?.[0]?.lat) &&
                (r.paradas?.[0]?.longitude ?? r.paradas?.[0]?.lng)
                  ? {
                      lat: parseFloat(
                        String(r.paradas[0].latitude ?? r.paradas[0].lat),
                      ),
                      lng: parseFloat(
                        String(r.paradas[0].longitude ?? r.paradas[0].lng),
                      ),
                    }
                  : null,
              lastLoc: r.coleta?.cidade || "Desconhecido",
              lastStop: r.paradas?.[0]?.endereco || "Nenhuma",
              speed: "—",
              timestamp: r.data_hora_solicitacao
                ? new Date(r.data_hora_solicitacao.replace(" ", "T")).getTime()
                : 0,
              paradas: r.paradas || [],
              tarifa_categoria_id: r.tarifa_categoria_id,
              categoria_id: r.categoria_id,
              tipo_pagamento: r.tipo_pagamento || "F",
              com_retorno: r.com_retorno || "0",
            };
          };

          const getTimestamp = (r: any) => {
            const dt = r.data_hora_solicitacao || r.data_hora_finalizacao || "";
            if (!dt) return 0;
            return new Date(dt.replace(" ", "T")).getTime();
          };

          const sortedRides = [...rawRides].sort(
            (a, b) => getTimestamp(b) - getTimestamp(a),
          );

          const inProgress = sortedRides
            .filter((r) => STATUS_ATIVO.has(r.status_solicitacao))
            .map(mapRide);
          const completed = sortedRides
            .filter((r) => ["F", "C", "N"].includes(r.status_solicitacao))
            .map(mapRide);

          setActiveRides(inProgress);
          setHistoryRides(completed);

          if (inProgress.length > 0 && !selectedCorrida) {
            setSelectedCorrida(inProgress[0]);
          }
        } else {
          if (!silent) {
            setActiveRides([]);
            setHistoryRides([]);
          }
        }

        // Tentar pegar localização da loja
        const companyIdStr = String(companyId);
        try {
          const compRes = await authFetch("/api/machine/companies");
          if (compRes.ok) {
            const compData = await compRes.json();
            const myComp = compData.companies?.find(
              (c: any) => String(c.id) === companyIdStr,
            );
            if (myComp) {
              setMachineCompanyData(myComp);
              if (myComp.lat && myComp.lng) {
                setStoreLocation([
                  parseFloat(myComp.lat),
                  parseFloat(myComp.lng),
                ]);
              } else if (myComp.latitude && myComp.longitude) {
                setStoreLocation([
                  parseFloat(myComp.latitude),
                  parseFloat(myComp.longitude),
                ]);
              }
            }
          }
        } catch (err) {
          logger.error("Erro ao buscar localização da loja:", err);
        }

        // Also fetch driver directory (names/phones) and driver positions
        try {
          const companyIdStr = String(companyId);
          if (companyIdStr) {
            const driversRes = await authFetch(
              `/api/db/company-drivers?company_id=${companyIdStr}&active_only=0`,
            );
            if (driversRes.ok) {
              const rows = await driversRes.json();
              const next: Record<
                string,
                { name: string; phone: string; status: string }
              > = {};
              if (Array.isArray(rows)) {
                for (const r of rows) {
                  const row = r as {
                    driverId?: unknown;
                    driverName?: unknown;
                    driverPhone?: unknown;
                    driverStatus?: unknown;
                  };
                  const id = String(row.driverId || "");
                  if (!id) continue;
                  next[id] = {
                    name: String(row.driverName || ""),
                    phone: String(row.driverPhone || ""),
                    status: String(row.driverStatus || ""),
                  };
                }
              }
              setDriverDirectory(next);
            }
          }
        } catch (err) {
          logger.warn("Erro ao buscar diretório de motoboys:", err);
        }

        try {
          const machineDriversRes = await authFetch("/api/machine/drivers");
          if (machineDriversRes.ok) {
            const machineDriversData = await machineDriversRes.json();
            const drivers = Array.isArray(machineDriversData?.drivers)
              ? machineDriversData.drivers
              : [];
            setDriverDirectory((prev) => {
              const merged = { ...prev };
              for (const d of drivers) {
                const row = d as {
                  id?: unknown;
                  nome?: unknown;
                  telefone?: unknown;
                  status?: unknown;
                };
                const id = String(row.id || "");
                if (!id) continue;
                const existing = merged[id];
                if (!existing || !existing.name) {
                  merged[id] = {
                    name: String(row.nome || existing?.name || ""),
                    phone: String(row.telefone || existing?.phone || ""),
                    status: String(row.status || existing?.status || ""),
                  };
                }
              }
              return merged;
            });
          }
        } catch (err) {
          if (mapDebug)
            console.debug("[Mapa] Falha ao buscar motoboys (Machine):", err);
        }

        try {
          const posRes = await authFetch(
            "/api/db/positions?max_age_minutes=720&limit=1000",
          );
          if (posRes.ok) {
            const posData = await posRes.json();
            const positionsRaw = Array.isArray(posData.positions)
              ? posData.positions
              : [];
            const normalized: DriverPosition[] = [];
            let dropped = 0;
            for (const p of positionsRaw) {
              const row = p as {
                machine_condutor_id?: unknown;
                latitude?: unknown;
                longitude?: unknown;
                speed?: unknown;
                heading?: unknown;
                machine_ride_id?: unknown;
                received_at?: unknown;
              };
              const id = String(row.machine_condutor_id || "");
              if (!id) {
                dropped++;
                continue;
              }
              const coords = normalizeLatLng(row.latitude, row.longitude);
              if (!coords) {
                dropped++;
                continue;
              }
              const receivedAt = String(
                row.received_at || new Date().toISOString(),
              );
              normalized.push({
                machine_condutor_id: id,
                latitude: coords.lat,
                longitude: coords.lng,
                speed: parseCoordNumber(row.speed) ?? 0,
                heading: parseCoordNumber(row.heading) ?? 0,
                machine_ride_id: row.machine_ride_id
                  ? String(row.machine_ride_id)
                  : null,
                received_at: receivedAt,
              });
            }
            setDriverPositions(normalized);
            knownDriverIdsRef.current = new Set(
              normalized.map((p) => String(p.machine_condutor_id)),
            );
            if (mapDebug) {
              console.debug("[Mapa] positions carregadas:", {
                raw: positionsRaw.length,
                normalized: normalized.length,
                dropped,
                source: posData?.source || "db",
              });
            }
          }
        } catch (err) {
          logger.error("Erro ao buscar posições dos motoboys:", err);
        }
      } catch (err: any) {
        logger.error("Erro ao buscar corridas:", err.message || err);
        if (!silent) {
          setError("Erro de conexão ao buscar corridas.");
          setActiveRides([]);
          setHistoryRides([]);
        }
      } finally {
        if (!silent) setLoading(false);
      }
    };

    fetchDados();

    // Auto-refresh every 30s as backup
    const interval = setInterval(() => fetchDados(true), 30_000);
    const handleVisibility = () => {
      if (!document.hidden) fetchDados(true);
    };
    document.addEventListener("visibilitychange", handleVisibility);

    // Supabase Realtime subscription com buffer de throttling de 1500ms
    // para evitar re-renders a cada ping individual de coordenadas
    const positionBuffer = new Map<string, DriverPosition>();
    let flushTimer: ReturnType<typeof setTimeout> | null = null;

    const flushBuffer = () => {
      if (positionBuffer.size === 0) return;
      const updates = Array.from(positionBuffer.values());
      positionBuffer.clear();
      setDriverPositions((prev) => {
        const map = new Map(
          prev.map((p) => [String(p.machine_condutor_id), p]),
        );
        updates.forEach((u) => map.set(String(u.machine_condutor_id), u));
        return Array.from(map.values());
      });
    };

    const channel = supabase
      .channel("driver-positions-realtime")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "driver_positions" },
        (payload) => {
          const newRecord = payload.new as {
            machine_condutor_id?: unknown;
            latitude?: unknown;
            longitude?: unknown;
            speed?: unknown;
            heading?: unknown;
            machine_ride_id?: unknown;
            received_at?: unknown;
          };
          const id = String(newRecord?.machine_condutor_id || "");
          if (!id) return;

          const allowed =
            companyDriverIdsRef.current.has(id) ||
            knownDriverIdsRef.current.has(id) ||
            activeDriverIdsRef.current.has(id);
          if (!allowed) return;

          const coords = normalizeLatLng(
            newRecord?.latitude,
            newRecord?.longitude,
          );
          if (!coords) return;

          // Acumula no buffer (substitui posição anterior do mesmo condutor)
          positionBuffer.set(id, {
            machine_condutor_id: id,
            latitude: coords.lat,
            longitude: coords.lng,
            speed: parseCoordNumber(newRecord.speed) ?? 0,
            heading: parseCoordNumber(newRecord.heading) ?? 0,
            machine_ride_id: newRecord.machine_ride_id
              ? String(newRecord.machine_ride_id)
              : null,
            received_at: String(
              newRecord.received_at || new Date().toISOString(),
            ),
          });

          // Debounce: aplica todas as atualizações acumuladas de uma vez a cada 1500ms
          if (flushTimer) clearTimeout(flushTimer);
          flushTimer = setTimeout(flushBuffer, 1500);
        },
      )
      .subscribe();

    return () => {
      clearInterval(interval);
      if (flushTimer) clearTimeout(flushTimer);
      document.removeEventListener("visibilitychange", handleVisibility);
      supabase.removeChannel(channel);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId, refreshKey]);

  const handleCreateRide = (ride: any) => {
    setActiveRides([ride, ...activeRides]);
    setSelectedCorrida(ride);
    setIsCreateModalOpen(false);
    showToast(`Corrida ${ride.id} criada com sucesso!`);
    setRefreshKey((k) => k + 1);
  };

  const handleExportCSV = () => {
    const escapeCSV = (val: string) => {
      const s = String(val ?? "");
      return s.includes(";") || s.includes('"') || s.includes("\n")
        ? `"${s.replace(/"/g, '""')}"`
        : s;
    };
    const header = "ID;Status;Tipo;Cliente;Empresa;Horario;Valor\n";
    const rows = historyRides
      .map((r) =>
        [r.id, r.status, r.tipo, r.cliente, r.empresa, r.horario, r.valor]
          .map((v) => escapeCSV(v))
          .join(";"),
      )
      .join("\n");
    const bom = "\uFEFF";
    const blob = new Blob([bom + header + rows], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "relatorio_corridas.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast("Relatório exportado com sucesso.");
  };

  const filteredActiveRides = useMemo(
    () =>
      activeRides.filter((r) => {
        const aTerm = activeSearch.toLowerCase().trim();
        const gTerm = globalSearch.toLowerCase().trim();

        const checkTerm = (term: string) =>
          !term
            ? true
            : r.id?.toString().toLowerCase().includes(term) ||
              r.codigoPedido?.toLowerCase().includes(term) ||
              r.cliente?.toLowerCase().includes(term) ||
              r.empresa?.toLowerCase().includes(term) ||
              r.motoboy?.nome?.toLowerCase().includes(term) ||
              r.motoboy?.placa?.toLowerCase().includes(term) ||
              r.coleta?.endereco?.toLowerCase().includes(term) ||
              r.entrega?.endereco?.toLowerCase().includes(term) ||
              r.status?.toLowerCase().includes(term);

        const st = String(r.status || "")
          .trim()
          .toLowerCase();
        const matchesFilter =
          activeFilter === "Todos" ? true : st === activeFilter.toLowerCase();

        return checkTerm(aTerm) && checkTerm(gTerm) && matchesFilter;
      }),
    [activeRides, activeSearch, globalSearch, activeFilter],
  );

  const aguardandoRides = useMemo(() => {
    const aguardandoStatuses = new Set(["P", "D", "G", "S"]);
    return filteredActiveRides.filter((r) => {
      const raw = String(r.rawStatus || "")
        .trim()
        .toUpperCase();
      return aguardandoStatuses.has(raw);
    });
  }, [filteredActiveRides]);

  const despachadoRides = useMemo(() => {
    const despachadoStatuses = new Set(["A", "E", "I"]);
    return filteredActiveRides.filter((r) => {
      const raw = String(r.rawStatus || "")
        .trim()
        .toUpperCase();
      return despachadoStatuses.has(raw);
    });
  }, [filteredActiveRides]);

  const busyDriverIds = useMemo(() => {
    const inRouteStatuses = new Set(["A", "E"]); // Aceita, Em andamento
    const ids = new Set<string>();
    for (const r of activeRides) {
      const raw = String(r.rawStatus || "")
        .trim()
        .toUpperCase();
      if (!inRouteStatuses.has(raw)) continue; // Ignora corridas sem motorista confirmado
      const dId = String(r.motoboy?.id_num || "").trim();
      if (dId && dId !== "") ids.add(dId);
    }
    return ids;
  }, [activeRides]);

  // Callback when a driver is clicked in FilaDinamica
  const handleDriverClick = useCallback(
    (driverId: string, isOnRide: boolean) => {
      // Switch to Radar tab
      setLeftPanelMode("machine");

      if (isOnRide) {
        // Find the ride assigned to this driver and select it
        const ride = activeRides.find((r) => {
          const raw = String(r.rawStatus || "")
            .trim()
            .toUpperCase();
          return (
            (raw === "A" || raw === "E") &&
            String(r.motoboy?.id_num || "").trim() === driverId
          );
        });
        if (ride) {
          setSelectedCorrida(ride);
          setFocusDriverId(null);
        }
      } else {
        // No ride — focus on driver position on map
        setSelectedCorrida(null);
        setFocusDriverId(driverId);
        setFocusKey((k) => k + 1);
      }
    },
    [activeRides],
  );

  const ridesToRender = useMemo(() => {
    return activeSubTab === "aguardando" ? aguardandoRides : despachadoRides;
  }, [activeSubTab, aguardandoRides, despachadoRides]);

  useEffect(() => {
    const currentList =
      activeSubTab === "aguardando" ? aguardandoRides : despachadoRides;
    if (selectedCorrida) {
      const exists = currentList.some((r) => r.id === selectedCorrida.id);
      if (!exists) {
        setSelectedCorrida(currentList.length > 0 ? currentList[0] : null);
      }
    } else if (currentList.length > 0) {
      setSelectedCorrida(currentList[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSubTab, aguardandoRides, despachadoRides]);

  const filteredHistoryRides = useMemo(
    () =>
      historyRides.filter((r) => {
        const hTerm = historySearch.toLowerCase().trim();
        const gTerm = globalSearch.toLowerCase().trim();

        const checkTerm = (term: string) =>
          !term
            ? true
            : r.id?.toString().toLowerCase().includes(term) ||
              r.codigoPedido?.toLowerCase().includes(term) ||
              r.cliente?.toLowerCase().includes(term) ||
              r.empresa?.toLowerCase().includes(term) ||
              r.motoboy?.nome?.toLowerCase().includes(term) ||
              r.motoboy?.placa?.toLowerCase().includes(term) ||
              r.coleta?.endereco?.toLowerCase().includes(term) ||
              r.entrega?.endereco?.toLowerCase().includes(term) ||
              r.status?.toLowerCase().includes(term) ||
              r.data?.toLowerCase().includes(term);

        const st = String(r.status || "")
          .trim()
          .toLowerCase();
        const matchesFilter =
          historyFilter === "Todas"
            ? true
            : historyFilter === "Concluídas"
              ? st === "concluída" || st === "concluido" || st === "concluído"
              : historyFilter === "Canceladas"
                ? st === "cancelada" ||
                  st === "não atendida" ||
                  st === "cancelado"
                : st === historyFilter.toLowerCase();

        return checkTerm(hTerm) && checkTerm(gTerm) && matchesFilter;
      }),
    [historyRides, historySearch, globalSearch, historyFilter],
  );

  const paginatedHistoryRides = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredHistoryRides.slice(start, start + itemsPerPage);
  }, [filteredHistoryRides, currentPage]);

  const totalPages = Math.ceil(filteredHistoryRides.length / itemsPerPage);

  // Resize handler
  const startResizing = () => {
    isResizing.current = true;
    document.addEventListener("mousemove", handleResize);
    document.addEventListener("mouseup", stopResizing);
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
  };

  const handleResize = (e: MouseEvent) => {
    if (!isResizing.current) return;
    const newHeight = window.innerHeight - e.clientY;
    if (newHeight >= 40 && newHeight < window.innerHeight - 100) {
      setHistoryHeight(newHeight);
    }
  };

  const stopResizing = () => {
    isResizing.current = false;
    document.removeEventListener("mousemove", handleResize);
    document.removeEventListener("mouseup", stopResizing);
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  };

  return (
    <div
      className="flex-1 flex flex-col lg:flex-row h-full min-h-0 bg-white overflow-hidden"
      style={{ minHeight: "100%" }}
    >
      {/* Left Sidebar */}
      <div className="w-full lg:w-[360px] bg-white border-r border-zinc-200 flex flex-col shrink-0 z-10 min-h-0">
        {/* Toggle Panel Mode */}
        <div className="px-4 pt-4 bg-zinc-50/50">
          <div className="flex bg-zinc-200/60 p-1 rounded-xl">
            <button
              onClick={() => setLeftPanelMode("lobby")}
              className={cn(
                "flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                leftPanelMode === "lobby"
                  ? "bg-white shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-zinc-900"
                  : "text-zinc-500 hover:text-zinc-700",
              )}
            >
              <Layers className="w-3.5 h-3.5" />
              Lobby
            </button>
            <button
              onClick={() => setLeftPanelMode("fila")}
              className={cn(
                "flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                leftPanelMode === "fila"
                  ? "bg-white shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-zinc-900"
                  : "text-zinc-500 hover:text-zinc-700",
              )}
            >
              <Clock className="w-3.5 h-3.5" />
              Fila
            </button>
            <button
              onClick={() => setLeftPanelMode("machine")}
              className={cn(
                "flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                leftPanelMode === "machine"
                  ? "bg-white shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-zinc-900"
                  : "text-zinc-500 hover:text-zinc-700",
              )}
            >
              <Truck className="w-3.5 h-3.5" />
              Radar
            </button>
          </div>
        </div>

        {leftPanelMode === "lobby" ? (
          <div className="flex-1 overflow-hidden mt-2 border-t border-zinc-200/50 flex flex-col">
            <PainelLobby
              rides={aguardandoRides}
              storeLocation={storeLocation}
              companyData={machineCompanyData}
              onRidesGrouped={() => setRefreshKey((k) => k + 1)}
            />
          </div>
        ) : leftPanelMode === "fila" ? (
          <div className="flex-1 overflow-hidden mt-2 border-t border-zinc-200/50 flex flex-col">
            <FilaDinamica
              driverPositions={driverPositions}
              driverDirectory={driverDirectory}
              busyDriverIds={busyDriverIds}
              storeLocation={storeLocation}
              onDriverClick={handleDriverClick}
            />
          </div>
        ) : (
          <>
            <div className="p-5 border-b border-zinc-100 space-y-4 bg-zinc-50/50 shrink-0">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-bold text-zinc-900 tracking-tight">
                  Corridas ativas{" "}
                  <span className="text-zinc-400 font-medium ml-1">
                    {filteredActiveRides.length}
                  </span>
                </h2>
                <button
                  onClick={() => {
                    setRedistributeRideData(null);
                    setIsCreateModalOpen(true);
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-bold shadow-md transition-all focus:ring-2 focus:ring-zinc-900/20 active:scale-95"
                >
                  <Plus strokeWidth={2.5} className="h-4 w-4" /> Nova Entrega
                </button>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1 group">
                  <Search
                    strokeWidth={1.5}
                    className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 group-focus-within:text-zinc-600 transition-colors"
                  />
                  <input
                    type="text"
                    placeholder="Buscar..."
                    value={activeSearch}
                    onChange={(e) => setActiveSearch(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all placeholder:text-zinc-400 shadow-sm"
                  />
                </div>
                <div className="relative">
                  <button
                    onClick={() =>
                      setActiveFilter((prev) =>
                        prev === "Todos"
                          ? "Aguardando"
                          : prev === "Aguardando"
                            ? "Em andamento"
                            : "Todos",
                      )
                    }
                    title={`Filtro atual: ${activeFilter}`}
                    className={cn(
                      "px-3 h-full flex items-center justify-center border text-xs font-semibold rounded-lg transition-all shadow-sm",
                      activeFilter !== "Todos"
                        ? "bg-zinc-900 text-white border-zinc-900"
                        : "bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50",
                    )}
                  >
                    <Filter strokeWidth={1.5} className="h-4 w-4 mr-1.5" />
                    <span>{activeFilter}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Subabas "Aguardando" e "Despachado" */}
            <div className="flex border-b border-zinc-100 bg-zinc-50/30 px-3 shrink-0">
              <button
                onClick={() => setActiveSubTab("aguardando")}
                className={cn(
                  "flex-1 py-3 text-xs font-bold text-center transition-all border-b-2 flex items-center justify-center gap-1.5",
                  activeSubTab === "aguardando"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent text-zinc-400 hover:text-zinc-600",
                )}
              >
                <span>Aguardando</span>
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded-full text-[10px] font-bold",
                    activeSubTab === "aguardando"
                      ? "bg-zinc-900 text-white"
                      : "bg-zinc-200 text-zinc-600",
                  )}
                >
                  {aguardandoRides.length}
                </span>
              </button>
              <button
                onClick={() => setActiveSubTab("despachado")}
                className={cn(
                  "flex-1 py-3 text-xs font-bold text-center transition-all border-b-2 flex items-center justify-center gap-1.5",
                  activeSubTab === "despachado"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent text-zinc-400 hover:text-zinc-600",
                )}
              >
                <span>Despachado</span>
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded-full text-[10px] font-bold",
                    activeSubTab === "despachado"
                      ? "bg-zinc-900 text-white"
                      : "bg-zinc-200 text-zinc-600",
                  )}
                >
                  {despachadoRides.length}
                </span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-zinc-50/30">
              {error ? (
                <div className="p-4 m-2 bg-red-50 text-red-600 rounded-lg border border-red-200 text-sm flex flex-col gap-2">
                  <span className="font-bold text-red-800">Falha na API</span>
                  <span>{error}</span>
                </div>
              ) : loading ? (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-2">
                  <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
                  <span className="text-sm">Carregando corridas...</span>
                </div>
              ) : ridesToRender.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <span className="text-sm">
                    {activeSubTab === "aguardando"
                      ? "Nenhuma corrida aguardando."
                      : "Nenhuma corrida despachada."}
                  </span>
                </div>
              ) : (
                ridesToRender.map((corrida) => {
                  const isSelected = selectedCorrida?.id === corrida.id;
                  const minutesAgo = corrida.timestamp
                    ? Math.max(
                        0,
                        Math.round((Date.now() - corrida.timestamp) / 60000),
                      )
                    : 0;
                  const timeLabel =
                    minutesAgo < 1
                      ? "Agora"
                      : minutesAgo < 60
                        ? `${minutesAgo} min`
                        : `${Math.floor(minutesAgo / 60)}h${minutesAgo % 60}m`;
                  const timeBg =
                    minutesAgo <= 5
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                      : minutesAgo <= 15
                        ? "bg-amber-50 text-amber-700 border-amber-200/60"
                        : "bg-rose-50 text-rose-700 border-rose-200/60";
                  const stopCount = Array.isArray(corrida.paradas)
                    ? corrida.paradas.length
                    : 0;
                  return (
                    <div
                      key={corrida.id}
                      onClick={() => setSelectedCorrida(corrida)}
                      className={cn(
                        "p-3.5 rounded-xl cursor-pointer transition-all border group",
                        isSelected
                          ? "bg-zinc-900 border-zinc-900 text-white shadow-lg shadow-zinc-900/20"
                          : "bg-white border-zinc-200 hover:border-zinc-300 hover:shadow-sm",
                      )}
                    >
                      {/* Header: Pedido # + Status badge + Time badge */}
                      <div className="flex justify-between items-start mb-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span
                              className={cn(
                                "font-bold tracking-tight text-sm",
                                isSelected ? "text-white" : "text-zinc-900",
                              )}
                            >
                              #{corrida.codigoPedido}
                            </span>
                            <span
                              className={cn(
                                "px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border",
                                isSelected
                                  ? "bg-white/10 text-white border-white/10"
                                  : corrida.rawStatus === "E" ||
                                      corrida.rawStatus === "A"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                                    : "bg-amber-50 text-amber-700 border-amber-200/60",
                              )}
                            >
                              {corrida.status}
                            </span>
                          </div>
                          <p
                            className={cn(
                              "text-[10px] mt-0.5 font-mono",
                              isSelected ? "text-zinc-500" : "text-zinc-400",
                            )}
                          >
                            OS: #{corrida.id} • {corrida.tipo}
                          </p>
                        </div>
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 tabular-nums",
                            isSelected
                              ? "bg-white/10 text-white border-white/10"
                              : timeBg,
                          )}
                        >
                          <Clock className="inline h-2.5 w-2.5 mr-0.5 -mt-0.5" />
                          {timeLabel}
                        </span>
                      </div>

                      {/* Info row: driver + client + value */}
                      <div
                        className={cn(
                          "flex items-center gap-3 text-[10px] mb-2.5",
                          isSelected ? "text-zinc-400" : "text-zinc-500",
                        )}
                      >
                        <div className="flex items-center gap-1 min-w-0 flex-1">
                          <Truck
                            strokeWidth={1.5}
                            className="h-3 w-3 shrink-0"
                          />
                          <span className="truncate">
                            {corrida.motoboy?.nome || "Sem motorista"}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 min-w-0 flex-1">
                          <User
                            strokeWidth={1.5}
                            className="h-3 w-3 shrink-0"
                          />
                          <span className="truncate">
                            {corrida.cliente || "Cliente"}
                          </span>
                        </div>
                        <span
                          className={cn(
                            "font-mono font-bold text-[11px] shrink-0",
                            isSelected ? "text-emerald-400" : "text-zinc-900",
                          )}
                        >
                          {formatCurrency(corrida.valor)}
                        </span>
                      </div>

                      {/* Timeline: coleta → entregas */}
                      <div
                        className={cn(
                          "relative pl-3 space-y-2.5 before:absolute before:left-[4px] before:top-1 before:bottom-1 before:w-px",
                          isSelected
                            ? "before:bg-zinc-700"
                            : "before:bg-zinc-200",
                        )}
                      >
                        <div className="relative">
                          <div
                            className={cn(
                              "absolute -left-[14px] top-1.5 w-1.5 h-1.5 rounded-full",
                              isSelected ? "bg-emerald-400" : "bg-emerald-500",
                            )}
                          />
                          <div className="flex gap-2 items-start">
                            <span
                              className={cn(
                                "text-[10px] font-mono mt-0.5 shrink-0 w-10",
                                isSelected ? "text-zinc-500" : "text-zinc-400",
                              )}
                            >
                              {corrida.coleta?.hora || "--:--"}
                            </span>
                            <p
                              className={cn(
                                "text-[11px] font-medium line-clamp-1",
                                isSelected ? "text-zinc-200" : "text-zinc-700",
                              )}
                            >
                              {corrida.coleta?.endereco ||
                                "Endereço não disponível"}
                            </p>
                          </div>
                        </div>
                        {(corrida.paradas || [])
                          .slice(0, 3)
                          .map((p: any, idx: number) => (
                            <div className="relative" key={p.id || idx}>
                              <div
                                className={cn(
                                  "absolute -left-[14px] top-1.5 w-1.5 h-1.5 rounded-full border border-current",
                                  isSelected
                                    ? "text-zinc-500 bg-zinc-900"
                                    : "text-zinc-300 bg-white",
                                )}
                              />
                              <div className="flex gap-2 items-start">
                                <span
                                  className={cn(
                                    "text-[10px] font-mono mt-0.5 shrink-0 w-10",
                                    isSelected
                                      ? "text-zinc-600"
                                      : "text-zinc-400",
                                  )}
                                >
                                  {corrida.entrega?.hora || "--:--"}
                                </span>
                                <p
                                  className={cn(
                                    "text-[11px] line-clamp-1",
                                    isSelected
                                      ? "text-zinc-400"
                                      : "text-zinc-500",
                                  )}
                                >
                                  {p.endereco || "Destino"}
                                  {p.bairro ? `, ${p.bairro}` : ""}
                                </p>
                              </div>
                            </div>
                          ))}
                        {stopCount > 3 && (
                          <div
                            className={cn(
                              "text-[10px] pl-12 font-medium",
                              isSelected ? "text-zinc-500" : "text-zinc-400",
                            )}
                          >
                            +{stopCount - 3} parada
                            {stopCount - 3 > 1 ? "s" : ""}
                          </div>
                        )}
                      </div>

                      {/* Footer: distance + stops */}
                      <div
                        className={cn(
                          "flex items-center gap-3 mt-2.5 pt-2 border-t text-[10px]",
                          isSelected
                            ? "border-zinc-800 text-zinc-500"
                            : "border-zinc-100 text-zinc-400",
                        )}
                      >
                        <div className="flex items-center gap-1">
                          <MapPin strokeWidth={1.5} className="h-2.5 w-2.5" />
                          <span>{corrida.distancia}</span>
                        </div>
                        {stopCount > 0 && (
                          <div className="flex items-center gap-1">
                            <Navigation
                              strokeWidth={1.5}
                              className="h-2.5 w-2.5"
                            />
                            <span>
                              {stopCount} entrega{stopCount > 1 ? "s" : ""}
                            </span>
                          </div>
                        )}
                        <div className="flex items-center gap-1">
                          <Store strokeWidth={1.5} className="h-2.5 w-2.5" />
                          <span className="truncate max-w-[100px]">
                            {corrida.empresa}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </>
        )}
      </div>

      {/* Main Content Area (Map) */}
      <div
        id="main-content-area"
        className="flex-1 flex flex-col min-w-0 h-full bg-white relative"
      >
        {/* Map Section */}
        <div className="flex-1 relative bg-zinc-100 border-b border-zinc-200 overflow-hidden min-h-[280px]">
          <div className="absolute inset-0 z-0">
            <ErrorBoundary>
              <MapContainer
                center={storeLocation || [-22.8265, -43.3155]}
                zoom={13}
                className="h-full w-full"
                zoomControl={false}
              >
              <TileLayer
                attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              />
              {/* Legend & Status Overlay */}
              <div className="absolute top-3 right-3 z-[400] flex flex-col items-end gap-2 pointer-events-none">
                <div
                  className={cn(
                    "px-3 py-1.5 rounded-full shadow-md text-xs font-bold text-white flex items-center gap-2 pointer-events-auto transition-all backdrop-blur-md",
                    onlineCount > 0
                      ? "bg-emerald-600/90 border border-emerald-500/50"
                      : "bg-blue-600/90 border border-blue-500/50",
                  )}
                >
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  <span>
                    {onlineCount > 0
                      ? `${onlineCount} motoboy${onlineCount > 1 ? "s" : ""} online`
                      : "Conectado • Nenhum motoboy ativo"}
                  </span>
                </div>
              </div>
              <MapController
                coords={
                  // Priority 1: focusDriverId (driver clicked in Fila)
                  focusDriverId && posByDriverId.get(focusDriverId)
                    ? [
                        posByDriverId.get(focusDriverId)!.latitude,
                        posByDriverId.get(focusDriverId)!.longitude,
                      ]
                    : // Priority 2: selected ride driver position
                      selectedCorrida?.motoboy?.id_num &&
                        posByDriverId.get(
                          String(selectedCorrida.motoboy.id_num),
                        )
                      ? [
                          posByDriverId.get(
                            String(selectedCorrida.motoboy.id_num),
                          )!.latitude,
                          posByDriverId.get(
                            String(selectedCorrida.motoboy.id_num),
                          )!.longitude,
                        ]
                      : selectedCorrida?.origin
                        ? [
                            selectedCorrida.origin.lat,
                            selectedCorrida.origin.lng,
                          ]
                        : storeLocation || null
                }
                rideId={
                  focusDriverId
                    ? `driver-${focusDriverId}`
                    : selectedCorrida?.id || "store-initial"
                }
                focusKey={focusKey}
              />
              {selectedCorrida?.origin && (
                <Marker
                  position={[
                    selectedCorrida.origin.lat,
                    selectedCorrida.origin.lng,
                  ]}
                  icon={storeIcon}
                >
                  <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                    Loja (Coleta)
                  </Tooltip>
                  <Popup>Coleta: {selectedCorrida.coleta?.endereco}</Popup>
                </Marker>
              )}
              {selfPosition && (
                <Marker
                  position={selfPosition}
                  icon={selfIcon}
                  zIndexOffset={1100}
                >
                  <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                    Sua localização
                  </Tooltip>
                </Marker>
              )}
              {storeLocation &&
                (!selectedCorrida ||
                  (selectedCorrida.origin &&
                    (Math.abs(selectedCorrida.origin.lat - storeLocation[0]) >
                      0.0001 ||
                      Math.abs(selectedCorrida.origin.lng - storeLocation[1]) >
                        0.0001))) && (
                  <Marker
                    position={[storeLocation[0], storeLocation[1]]}
                    icon={storeIcon}
                  >
                    <Popup>Sua Loja: {companyName}</Popup>
                  </Marker>
                )}
              {selectedCorrida?.destination && (
                <Marker
                  position={[
                    selectedCorrida.destination.lat,
                    selectedCorrida.destination.lng,
                  ]}
                  icon={dropoffIcon}
                >
                  <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                    Entrega
                  </Tooltip>
                  <Popup>Entrega: {selectedCorrida.entrega?.endereco}</Popup>
                </Marker>
              )}

              {/* All active drivers */}
              {(Array.from(posByDriverId.values()) as DriverPosition[]).map(
                (pos) => {
                  const matchingRide = activeRides.find(
                    (r) =>
                      String(r.motoboy?.id_num) ===
                      String(pos.machine_condutor_id),
                  );
                  const directoryEntry =
                    driverDirectory[String(pos.machine_condutor_id)];
                  const driverName =
                    String(
                      matchingRide?.motoboy?.nome || directoryEntry?.name || "",
                    ).trim() || `Motoboy ${pos.machine_condutor_id}`;
                  const driverPhone = String(
                    directoryEntry?.phone || "",
                  ).trim();
                  const driverStatus = String(
                    directoryEntry?.status || "",
                  ).trim();
                  const isSelectedDriver =
                    selectedDriverId &&
                    String(pos.machine_condutor_id) === selectedDriverId;
                  const isFaded = selectedCorrida && !isSelectedDriver;

                  return (
                    <Marker
                      key={`driver-${pos.machine_condutor_id}`}
                      position={[pos.latitude, pos.longitude]}
                      icon={isSelectedDriver ? driverIconSelected : driverIcon}
                      zIndexOffset={1000}
                      opacity={isFaded ? 0.4 : 1}
                    >
                      <Tooltip direction="top" offset={[0, -12]} opacity={0.95}>
                        {driverName}
                        {driverStatus ? ` • ${driverStatus}` : ""}
                      </Tooltip>
                      <Popup className="custom-popup">
                        <div className="p-1">
                          <div className="flex items-center gap-2 mb-1">
                            <div className="h-6 w-6 rounded-full bg-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">
                              {driverName.charAt(0).toUpperCase()}
                            </div>
                            <span className="font-bold text-zinc-900">
                              {driverName}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <p className="text-[10px] text-zinc-500 flex items-center gap-1">
                              <Clock className="h-3 w-3" /> Atualizado há{" "}
                              {Math.max(
                                0,
                                Math.round(
                                  (Date.now() -
                                    new Date(pos.received_at).getTime()) /
                                    60000,
                                ),
                              )}{" "}
                              min
                            </p>
                            {driverPhone && (
                              <p className="text-[10px] text-zinc-600">
                                Contato: {driverPhone}
                              </p>
                            )}
                            {driverStatus && (
                              <p className="text-[10px] text-zinc-600">
                                Status: {driverStatus}
                              </p>
                            )}
                            {pos.speed > 0 && (
                              <p className="text-[10px] text-emerald-600 font-bold">
                                Velocidade: {Math.round(pos.speed)} km/h
                              </p>
                            )}
                          </div>
                        </div>
                      </Popup>
                    </Marker>
                  );
                },
              )}
            </MapContainer>
            </ErrorBoundary>
          </div>

          {!selectedCorrida ? (
            <div
              className="absolute top-3 left-1/2 -translate-x-1/2 pointer-events-none"
              style={{ zIndex: 400 }}
            >
              <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full shadow-md border border-zinc-200/60 flex items-center gap-2 text-xs font-medium text-zinc-500">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Selecione uma corrida para ver os pontos de coleta e entrega no
                mapa
              </div>
            </div>
          ) : (
            <>
              <div
                className="absolute top-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-3xl pointer-events-none"
                style={{ zIndex: 400 }}
              >
                <div className="bg-white/95 backdrop-blur-md rounded-xl shadow-lg border border-zinc-200/50 flex flex-wrap sm:flex-nowrap divide-y sm:divide-y-0 sm:divide-x divide-zinc-100 pointer-events-auto">
                  <div className="flex w-full sm:w-1/2 divide-x divide-zinc-100">
                    <StatColumn
                      icon={<Navigation className="h-4 w-4 text-emerald-500" />}
                      label="Localização"
                      value={
                        selectedCorrida.motoboy?.id_num &&
                        posByDriverId.get(
                          String(selectedCorrida.motoboy.id_num),
                        )
                          ? `Lat ${posByDriverId.get(String(selectedCorrida.motoboy.id_num))!.latitude.toFixed(4)}, Lng ${posByDriverId.get(String(selectedCorrida.motoboy.id_num))!.longitude.toFixed(4)}`
                          : selectedCorrida.lastLoc || "Desconhecido"
                      }
                    />
                    <StatColumn
                      icon={<MapPin className="h-4 w-4 text-zinc-400" />}
                      label="Última parada"
                      value={selectedCorrida.lastStop || "Nenhuma"}
                    />
                  </div>
                  <div className="flex w-full sm:w-1/2 divide-x divide-zinc-100">
                    <StatColumn
                      icon={<ChevronRight className="h-4 w-4 text-zinc-400" />}
                      label={
                        selfToPickupKm !== null ? "Você → Coleta" : "Distância"
                      }
                      value={
                        selfToPickupKm !== null
                          ? `${selfToPickupKm.toFixed(2)} km`
                          : selectedCorrida.distancia || "0 km"
                      }
                    />
                    <StatColumn
                      icon={<Clock className="h-4 w-4 text-zinc-400" />}
                      label="Velocidade"
                      value={
                        selectedCorrida.motoboy?.id_num &&
                        posByDriverId.get(
                          String(selectedCorrida.motoboy.id_num),
                        )
                          ? `${Math.round(posByDriverId.get(String(selectedCorrida.motoboy.id_num))!.speed || 0)} km/h`
                          : "0 km/h"
                      }
                    />
                  </div>
                </div>
              </div>

              <div
                className="absolute bottom-4 left-4 right-4 pointer-events-none"
                style={{ zIndex: 400 }}
              >
                <div className="bg-white rounded-xl shadow-lg border border-zinc-200/80 overflow-hidden flex flex-col pointer-events-auto">
                  <div className="flex border-b border-zinc-100 bg-zinc-50/50 overflow-x-auto hide-scrollbar">
                    {[
                      "Detalhes do pedido",
                      "Informações do motorista",
                      "Veículo",
                      "Informações do cliente",
                    ].map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={cn(
                          "px-4 py-2.5 text-xs font-semibold whitespace-nowrap transition-all border-b-2",
                          activeTab === tab
                            ? "border-emerald-500 text-zinc-900 bg-white"
                            : "border-transparent text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100/50",
                        )}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>

                  <div className="p-4 sm:p-5">
                    <AnimatePresence mode="wait">
                      {activeTab === "Informações do motorista" ? (
                        <motion.div
                          key="driver"
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          className="flex flex-col sm:flex-row gap-6 items-start sm:items-center justify-between"
                        >
                          <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-800 font-bold text-xl shadow-sm shrink-0">
                              {selectedCorrida.motoboy?.nome
                                ? selectedCorrida.motoboy.nome
                                    .charAt(0)
                                    .toUpperCase()
                                : "M"}
                            </div>
                            <div>
                              <h3 className="text-lg font-bold text-zinc-900 tracking-tight">
                                {selectedCorrida.motoboy?.nome ||
                                  "Sem motorista"}
                              </h3>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                {selectedCorrida.motoboy?.nome ? (
                                  <>
                                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                                    <span className="text-xs font-medium text-zinc-500">
                                      Motorista Ativo
                                    </span>
                                  </>
                                ) : (
                                  <span className="text-xs font-medium text-zinc-400">
                                    Aguardando motorista
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-x-8 gap-y-4 text-sm grow sm:justify-end border-l border-zinc-100 pl-6 ml-2">
                            <InfoBlock
                              label="Experiência"
                              value={selectedCorrida.motoboy?.exp || "-"}
                            />
                            <InfoBlock
                              label="CNH"
                              value={selectedCorrida.motoboy?.cnh || "-"}
                            />
                            <InfoBlock
                              label="Documento"
                              value={selectedCorrida.motoboy?.id_num || "-"}
                            />
                          </div>

                          <div className="flex gap-2 shrink-0 w-full sm:w-auto">
                            <button
                              onClick={() => {
                                const phone =
                                  driverDirectory[
                                    String(selectedCorrida.motoboy?.id_num)
                                  ]?.phone ||
                                  selectedCorrida.telefoneMotorista ||
                                  "";
                                if (phone) {
                                  window.open(
                                    `tel:${phone.replace(/\D/g, "")}`,
                                    "_self",
                                  );
                                } else {
                                  showToast(
                                    `Telefone de ${selectedCorrida.motoboy?.nome || "Motorista"} não disponível.`,
                                  );
                                }
                              }}
                              className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-900 text-sm font-semibold shadow-sm transition-all"
                            >
                              <Phone className="h-3.5 w-3.5 fill-current" />{" "}
                              Ligar
                            </button>
                            <button
                              onClick={() => {
                                const phone =
                                  driverDirectory[
                                    String(selectedCorrida.motoboy?.id_num)
                                  ]?.phone ||
                                  selectedCorrida.telefoneMotorista ||
                                  "";
                                if (phone) {
                                  let cleanPhone = phone.replace(/\D/g, "");
                                  if (!cleanPhone.startsWith("55"))
                                    cleanPhone = "55" + cleanPhone;
                                  window.open(
                                    `https://wa.me/${cleanPhone}`,
                                    "_blank",
                                  );
                                } else {
                                  showToast(
                                    `Telefone de ${selectedCorrida.motoboy?.nome || "Motorista"} não disponível para chat.`,
                                  );
                                }
                              }}
                              className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 text-sm font-semibold shadow-sm transition-all"
                            >
                              <MessageSquare className="h-3.5 w-3.5" /> WhatsApp
                            </button>
                          </div>
                        </motion.div>
                      ) : activeTab === "Detalhes do pedido" ? (
                        <motion.div
                          key="order"
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          className="flex flex-col sm:flex-row gap-6 items-start sm:items-center justify-between"
                        >
                          <div className="flex items-center gap-4">
                            <div>
                              <h3 className="text-lg font-bold text-zinc-900 tracking-tight">
                                Pedido #{selectedCorrida.codigoPedido}
                                <span className="text-xs font-mono font-normal text-zinc-400 ml-2">
                                  OS: #{selectedCorrida.id}
                                </span>
                              </h3>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <Store className="h-3.5 w-3.5 text-zinc-400" />
                                <span className="text-xs font-medium text-zinc-500">
                                  {selectedCorrida.empresa || "-"}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-x-8 gap-y-4 text-sm grow sm:justify-end border-l border-zinc-100 pl-6 ml-2">
                            <InfoBlock
                              label="Tipo"
                              value={selectedCorrida.tipo || "-"}
                            />
                            <InfoBlock
                              label="Criado em"
                              value={selectedCorrida.horario || "-"}
                            />
                            <InfoBlock
                              label="Valor"
                              value={
                                selectedCorrida.valor
                                  ? formatCurrency(selectedCorrida.valor)
                                  : "-"
                              }
                            />
                          </div>
                          <div className="flex gap-2 shrink-0 w-full sm:w-auto">
                            {[
                              "Concluída",
                              "Cancelada",
                              "Não atendida",
                            ].includes(selectedCorrida.status) ? (
                              <div className="px-4 py-2 bg-zinc-100 text-zinc-500 rounded-lg text-sm font-semibold border border-zinc-200">
                                Corrida Finalizada
                              </div>
                            ) : (
                              <>
                                <button
                                  onClick={() =>
                                    handleOpenTracking(selectedCorrida.id)
                                  }
                                  disabled={
                                    loadingTracking ===
                                    String(selectedCorrida.id)
                                  }
                                  className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 bg-emerald-600 text-white border border-emerald-500 rounded-lg hover:bg-emerald-700 text-sm font-semibold shadow-sm transition-all disabled:opacity-50"
                                >
                                  {loadingTracking ===
                                  String(selectedCorrida.id) ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    <ExternalLink className="h-3.5 w-3.5" />
                                  )}
                                  <span>Rastreio ao Vivo</span>
                                </button>
                                <button
                                  onClick={async () => {
                                    try {
                                      const res = await authFetch(
                                        "/api/machine/rides/cancel",
                                        {
                                          method: "POST",
                                          headers: {
                                            "Content-Type": "application/json",
                                          },
                                          body: JSON.stringify({
                                            id_mch: selectedCorrida.id,
                                            motivo_id: 7,
                                          }),
                                        },
                                      );
                                      if (res.ok) {
                                        showToast(
                                          `Corrida #${selectedCorrida.id} cancelada com sucesso.`,
                                        );
                                        const canceledRide = {
                                          ...selectedCorrida,
                                          status: "Cancelada",
                                        };
                                        setActiveRides(
                                          activeRides.filter(
                                            (r) => r.id !== selectedCorrida.id,
                                          ),
                                        );
                                        setHistoryRides([
                                          canceledRide,
                                          ...historyRides,
                                        ]);
                                        setSelectedCorrida(null);
                                      } else {
                                        const d = await res
                                          .json()
                                          .catch(() => ({}));
                                        const errMsg =
                                          d?.error ||
                                          d?.details?.errors?.[0]?.message ||
                                          "Erro ao cancelar a corrida";
                                        showToast(`Erro: ${errMsg}`);
                                      }
                                    } catch (err) {
                                      showToast(
                                        "Falha de conexão ao cancelar corrida.",
                                      );
                                    }
                                  }}
                                  className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 bg-red-50 text-red-600 border border-red-200/50 rounded-lg hover:bg-red-100 text-sm font-semibold shadow-sm transition-all"
                                >
                                  <Ban className="h-3.5 w-3.5" /> Cancelar
                                </button>
                              </>
                            )}
                          </div>
                        </motion.div>
                      ) : activeTab === "Veículo" ? (
                        <motion.div
                          key="vehicle"
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          className="flex flex-col sm:flex-row gap-6 items-start sm:items-center justify-between"
                        >
                          <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-800 font-bold text-xl shadow-sm shrink-0">
                              <Truck className="w-6 h-6 text-zinc-400" />
                            </div>
                            <div>
                              <h3 className="text-lg font-bold text-zinc-900 tracking-tight">
                                {selectedCorrida.motoboy?.veiculo ||
                                  "Motocicleta Padrão"}
                              </h3>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-xs font-medium text-zinc-500 uppercase tracking-widest">
                                  {selectedCorrida.motoboy?.placa || "XXX-0000"}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-x-8 gap-y-4 text-sm grow sm:justify-end border-l border-zinc-100 pl-6 ml-2">
                            <InfoBlock label="Cor" value="Não informada" />
                            <InfoBlock label="Ano" value="-" />
                            <InfoBlock label="Licenciamento" value="Regular" />
                          </div>
                        </motion.div>
                      ) : activeTab === "Informações do cliente" ? (
                        <motion.div
                          key="customer"
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          className="flex flex-col sm:flex-row gap-6 items-start sm:items-center justify-between"
                        >
                          <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center text-indigo-800 font-bold text-xl shadow-sm shrink-0">
                              {selectedCorrida.cliente
                                ? selectedCorrida.cliente
                                    .charAt(0)
                                    .toUpperCase()
                                : "C"}
                            </div>
                            <div>
                              <h3 className="text-lg font-bold text-zinc-900 tracking-tight">
                                {selectedCorrida.cliente || "Cliente"}
                              </h3>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-xs font-medium text-zinc-500">
                                  Ver perfil completo
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-x-8 gap-y-4 text-sm grow sm:justify-end border-l border-zinc-100 pl-6 ml-2">
                            <InfoBlock
                              label="Telefone"
                              value={
                                selectedCorrida.telefoneCliente ||
                                "Não informado"
                              }
                            />
                            <InfoBlock label="Pedidos" value="Pedido atual" />
                          </div>
                          <div className="flex gap-2 shrink-0 w-full sm:w-auto">
                            <button
                              onClick={() => {
                                const phone =
                                  selectedCorrida.telefoneCliente || "";
                                if (phone) {
                                  window.open(
                                    `tel:${phone.replace(/\D/g, "")}`,
                                    "_self",
                                  );
                                } else {
                                  showToast(
                                    "Telefone do cliente não disponível.",
                                  );
                                }
                              }}
                              className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-900 text-sm font-semibold shadow-sm transition-all"
                            >
                              <Phone className="h-3.5 w-3.5 fill-current" />{" "}
                              Ligar para Cliente
                            </button>
                            <button
                              onClick={() => {
                                const phone =
                                  selectedCorrida.telefoneCliente || "";
                                if (phone) {
                                  let cleanPhone = phone.replace(/\D/g, "");
                                  if (!cleanPhone.startsWith("55"))
                                    cleanPhone = "55" + cleanPhone;
                                  window.open(
                                    `https://wa.me/${cleanPhone}`,
                                    "_blank",
                                  );
                                } else {
                                  showToast(
                                    "Telefone do cliente não disponível para chat.",
                                  );
                                }
                              }}
                              className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 text-sm font-semibold shadow-sm transition-all"
                            >
                              <MessageSquare className="h-3.5 w-3.5" /> WhatsApp
                              Cliente
                            </button>
                          </div>
                        </motion.div>
                      ) : null}
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Seção de Histórico com Altura Dinâmica */}
        <div
          className="flex flex-col bg-white border-t border-zinc-200 relative shrink-0 overflow-hidden"
          style={{ height: `${historyHeight}px` }}
        >
          {/* Barra de Arraste (Resize Handle) */}
          <div
            onMouseDown={startResizing}
            className="absolute -top-1.5 left-0 right-0 h-4 cursor-row-resize z-50 flex items-center justify-center group/handle"
          >
            <div className="w-16 h-1 bg-zinc-300 rounded-full group-hover/handle:bg-zinc-500 transition-all"></div>
          </div>

          {/* Header do Histórico */}
          <div className="p-4 border-b border-zinc-200 flex flex-col sm:flex-row gap-3 items-center justify-between bg-zinc-50/50 shrink-0">
            <div className="relative w-full sm:max-w-xs group">
              <Search
                strokeWidth={1.5}
                className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 group-focus-within:text-zinc-600 transition-colors"
              />
              <input
                type="text"
                placeholder="Buscar no histórico..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all placeholder:text-zinc-400 shadow-sm"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex gap-1 bg-zinc-100 p-1 rounded-lg">
                {["Todas", "Concluídas", "Canceladas"].map((status) => (
                  <button
                    key={status}
                    onClick={() => setHistoryFilter(status)}
                    className={cn(
                      "px-3 py-1 text-xs font-semibold rounded-md transition-all",
                      historyFilter === status
                        ? "bg-white text-zinc-900 shadow-sm"
                        : "text-zinc-500 hover:text-zinc-700",
                    )}
                  >
                    {status}
                  </button>
                ))}
              </div>
              <button
                onClick={handleExportCSV}
                className="flex items-center gap-2 px-3 py-1.5 bg-white border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 hover:text-zinc-900 text-xs font-medium transition-all shadow-sm"
              >
                <FileDown strokeWidth={1.5} className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Exportar</span>
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-auto min-h-0">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="sticky top-0 bg-zinc-50/95 backdrop-blur-sm z-10 shadow-[0_1px_0_rgba(0,0,0,0.1)]">
                <tr className="text-zinc-500 text-[10px] font-bold uppercase tracking-wider">
                  <th className="px-4 py-2">ID / Status</th>
                  <th className="px-4 py-2">Data</th>
                  <th className="px-4 py-2">Horário</th>
                  <th className="px-4 py-2">Motoboy</th>
                  <th className="px-4 py-2">Cliente</th>
                  <th className="px-4 py-2">Empresa</th>
                  <th className="px-4 py-2">Rota</th>
                  <th className="px-4 py-2 text-right">Valor</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {error ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-4 py-8 text-center text-red-500 bg-red-50/50"
                    >
                      <span className="font-bold">
                        Erro ao carregar histórico:
                      </span>{" "}
                      {error}
                    </td>
                  </tr>
                ) : loading ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-4 py-8 text-center text-zinc-500"
                    >
                      Carregando histórico...
                    </td>
                  </tr>
                ) : filteredHistoryRides.length === 0 ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-4 py-8 text-center text-zinc-500"
                    >
                      Nenhum histórico encontrado.
                    </td>
                  </tr>
                ) : (
                  paginatedHistoryRides.map((corrida, idx) => (
                    <motion.tr
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      key={corrida.id}
                      className="hover:bg-zinc-50/80 transition-colors group"
                    >
                      <td className="px-4 py-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-bold text-zinc-900 text-xs tracking-tight">
                            Pedido #{corrida.codigoPedido}
                          </span>
                          <span className="font-mono text-zinc-400 text-[10px]">
                            OS: #{corrida.id}
                          </span>
                          <span
                            className={cn(
                              "inline-flex w-fit items-center px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider mt-0.5",
                              corrida.status === "Em andamento"
                                ? "bg-blue-100 text-blue-700"
                                : corrida.status === "Coletando"
                                  ? "bg-amber-100 text-amber-700"
                                  : corrida.status === "Concluída"
                                    ? "bg-emerald-100 text-emerald-700"
                                    : "bg-rose-100 text-rose-700",
                            )}
                          >
                            {corrida.status}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2 text-zinc-600 font-medium text-xs">
                        {corrida.data}
                      </td>
                      <td className="px-4 py-2 text-zinc-500 text-xs">
                        {corrida.horario}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 rounded-full bg-zinc-900 flex items-center justify-center text-white font-bold text-[9px] ring-2 ring-white shadow-sm">
                            {(corrida.motoboy?.nome || "Sem motorista").charAt(
                              0,
                            )}
                          </div>
                          <span className="font-medium text-zinc-900 text-xs">
                            {corrida.motoboy?.nome || "Sem motorista"}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex flex-col text-zinc-800">
                          <div className="flex items-center gap-1.5 font-medium text-xs">
                            <User
                              strokeWidth={1.5}
                              className="h-3 w-3 text-zinc-400 shrink-0"
                            />
                            <span className="line-clamp-1">
                              {corrida.cliente}
                            </span>
                          </div>
                          {corrida.telefoneCliente && (
                            <span className="font-mono text-zinc-400 text-[10px] pl-4">
                              {corrida.telefoneCliente}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-1.5 text-zinc-600">
                          <Store
                            strokeWidth={1.5}
                            className="h-3 w-3 text-zinc-400"
                          />
                          <span className="font-medium text-xs">
                            {corrida.empresa}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-1.5 text-zinc-500">
                          <MapPin strokeWidth={1.5} className="h-3 w-3" />
                          <span className="font-mono text-[11px]">
                            {corrida.distancia}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className="font-mono font-medium text-zinc-900 text-xs">
                          {formatCurrency(corrida.valor)}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              setSelectedCorrida(corrida);
                              document
                                .getElementById("main-content-area")
                                ?.scrollTo({ top: 0, behavior: "smooth" });
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-zinc-600 bg-white border border-zinc-200 hover:border-zinc-300 hover:text-zinc-900 hover:bg-zinc-50 rounded-md transition-all shadow-sm"
                            title="Ver no mapa"
                          >
                            <MapIcon
                              strokeWidth={1.5}
                              className="h-2.5 w-2.5 text-indigo-500"
                            />
                            Trajeto
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setRedistributeRideData(corrida);
                              setIsCreateModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 hover:border-emerald-300 hover:bg-emerald-100 rounded-md transition-all shadow-sm"
                            title="Recriar esta corrida idêntica"
                          >
                            <Plus strokeWidth={2} className="h-2.5 w-2.5" />
                            Redistribuir
                          </button>
                          {(corrida.rawStatus === "F" ||
                            corrida.status === "Concluída") && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                try {
                                  const res = await fetch(
                                    `/api/machine/rides/receipt?solicitacao_id=${corrida.id}`,
                                  );
                                  if (res.ok) {
                                    const data = await res.json();
                                    // Open receipt in new tab as formatted page
                                    const w = window.open("", "_blank");
                                    if (w) {
                                      w.document.write(
                                        `<html><head><title>Recibo #${corrida.id}</title><style>body{font-family:system-ui,-apple-system,sans-serif;padding:2rem;max-width:600px;margin:0 auto;color:#18181b}pre{white-space:pre-wrap;font-size:13px;background:#f4f4f5;padding:1.5rem;border-radius:12px;border:1px solid #e4e4e7}</style></head><body><h2>Recibo — Corrida #${corrida.id}</h2><pre>${JSON.stringify(data, null, 2)}</pre></body></html>`,
                                      );
                                      w.document.close();
                                    }
                                  } else {
                                    alert(
                                      "Recibo não disponível para esta corrida.",
                                    );
                                  }
                                } catch {
                                  alert("Erro ao buscar recibo.");
                                }
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-zinc-600 bg-white border border-zinc-200 hover:border-zinc-300 hover:text-zinc-900 hover:bg-zinc-50 rounded-md transition-all shadow-sm"
                              title="Ver recibo"
                            >
                              <FileText
                                strokeWidth={1.5}
                                className="h-2.5 w-2.5 text-emerald-500"
                              />
                              Recibo
                            </button>
                          )}
                        </div>
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2.5 border-t border-zinc-200 bg-zinc-50/50 flex flex-col sm:flex-row items-center justify-between gap-4 shrink-0">
            <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
              Mostrando{" "}
              {Math.min(
                filteredHistoryRides.length,
                (currentPage - 1) * itemsPerPage + 1,
              )}
              -
              {Math.min(
                filteredHistoryRides.length,
                currentPage * itemsPerPage,
              )}{" "}
              de {filteredHistoryRides.length} corridas
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 border border-zinc-200 rounded-md bg-white text-zinc-500 hover:bg-zinc-50 disabled:opacity-50 text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all"
              >
                Anterior
              </button>
              <button
                onClick={() =>
                  setCurrentPage((p) => Math.min(totalPages, p + 1))
                }
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 border border-zinc-200 rounded-md bg-white text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all"
              >
                Próxima
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* End of main-content-area */}
      <RideMapModal
        isOpen={!!selectedHistoryMap}
        onClose={() => setSelectedHistoryMap(null)}
        corrida={selectedHistoryMap}
      />

      <CreateRideModal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setRedistributeRideData(null);
        }}
        onSave={handleCreateRide}
        currentCompany={
          machineCompanyData
            ? { ...currentCompany, ...machineCompanyData }
            : currentCompany
        }
        initialData={redistributeRideData}
      />

      <RideChatModal
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        corrida={selectedCorrida}
      />

      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="fixed bottom-6 right-6 z-[9999] bg-zinc-900 text-white px-4 py-3 border border-zinc-800 rounded-xl shadow-2xl flex items-center gap-3"
          >
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-sm font-medium">{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatColumn({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex-1 min-w-0 px-3 sm:px-4 py-2.5 flex flex-col gap-1">
      <div className="flex items-center gap-2 text-zinc-500 text-[10px] sm:text-xs font-semibold uppercase tracking-wider">
        <span className="shrink-0">{icon}</span>
        <span className="truncate">{label}</span>
      </div>
      <div className="text-xs sm:text-sm font-bold text-zinc-900 truncate pl-5 sm:pl-6">
        {value}
      </div>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-semibold text-zinc-500">{label}</span>
      <span className="text-sm font-bold text-zinc-900">{value}</span>
    </div>
  );
}
