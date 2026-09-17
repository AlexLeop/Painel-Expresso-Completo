import { logger } from "@/lib/logger";
import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { X, Map as MapIcon } from "lucide-react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  useMap,
  Tooltip,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix for default marker icons in Leaflet with bundlers
import { ErrorBoundary } from "../ErrorBoundary";
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const pickupIcon = L.divIcon({
  html: `
    <div title="Coleta" style="width: 34px; height: 34px; border-radius: 9999px; background: #111827; border: 2px solid #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.18); display: flex; align-items: center; justify-content: center;">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>
        <path d="M12 22V12"/>
        <path d="M3.3 7.3 12 12l8.7-4.7"/>
      </svg>
    </div>
  `,
  className: "",
  iconSize: [34, 34],
  iconAnchor: [17, 17],
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
  html: `<div title="Loja (Coleta)" style="background-color: #2563eb; padding: 8px; border-radius: 9999px; border: 2px solid white; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1); color: white; display: flex; align-items: center; justify-content: center;">
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

interface RideMapModalProps {
  isOpen: boolean;
  onClose: () => void;
  corrida: any;
}

// Custom hook to fit bounds after route is loaded
function MapBounds({
  routeCoordinates,
}: {
  routeCoordinates: [number, number][];
}) {
  const map = useMap();
  useEffect(() => {
    if (routeCoordinates.length > 0) {
      const bounds = L.latLngBounds(routeCoordinates);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [map, routeCoordinates]);
  return null;
}

export function RideMapModal({ isOpen, onClose, corrida }: RideMapModalProps) {
  const [routeCoordinates, setRouteCoordinates] = useState<[number, number][]>(
    [],
  );
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !corrida) return;

    const fetchRoute = async () => {
      setIsLoadingRoute(true);
      setRouteError(null);
      try {
        const { origin, destination } = corrida;
        // OSRM coordinates format: lon,lat
        const response = await fetch(
          `https://router.project-osrm.org/route/v1/driving/${origin.lng},${origin.lat};${destination.lng},${destination.lat}?overview=full&geometries=geojson`,
        );
        const data = await response.json();

        if (data.code === "Ok" && data.routes.length > 0) {
          // OSRM returns GeoJSON coordinates as [lon, lat], Leaflet expects [lat, lon]
          const coords = data.routes[0].geometry.coordinates.map(
            (c: [number, number]) => [c[1], c[0]],
          );
          setRouteCoordinates(coords);
        } else {
          setRouteError("Não foi possível encontrar uma rota.");
          setRouteCoordinates([
            [origin.lat, origin.lng],
            [destination.lat, destination.lng],
          ]);
        }
      } catch (error) {
        logger.error("Erro ao buscar rota:", error);
        setRouteError("Erro ao calcular rota.");
        // Fallback to straight line
        const { origin, destination } = corrida;
        setRouteCoordinates([
          [origin.lat, origin.lng],
          [destination.lat, destination.lng],
        ]);
      } finally {
        setIsLoadingRoute(false);
      }
    };

    fetchRoute();
  }, [isOpen, corrida]);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen || !corrida) return null;

  const originLatLon: [number, number] = [
    corrida.origin.lat,
    corrida.origin.lng,
  ];
  const destLatLon: [number, number] = [
    corrida.destination.lat,
    corrida.destination.lng,
  ];
  const motoboyName = (() => {
    const mb = corrida.motoboy;
    if (!mb) return "";
    if (typeof mb === "string") return mb;
    if (typeof mb === "object" && mb !== null) {
      const maybe = mb as { nome?: unknown; name?: unknown };
      return String(maybe.nome || maybe.name || "");
    }
    return "";
  })();

  return typeof document !== "undefined"
    ? createPortal(
        <AnimatePresence>
          <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
              className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
            />

            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 260 }}
              className="fixed top-0 right-0 h-full w-full max-w-3xl lg:max-w-4xl bg-white shadow-2xl z-10 flex flex-col pointer-events-auto border-l border-zinc-200"
            >
              {/* Header */}
              <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/80 backdrop-blur-xs shrink-0">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-2xl shadow-sm shadow-indigo-500/20 text-white">
                    <MapIcon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-2 py-0.5 rounded-full">
                        Corridas & Rastreamento
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-zinc-900 mt-0.5">
                      Rota da Corrida #{corrida.id}
                    </h2>
                    <p className="text-xs text-zinc-500">
                      {motoboyName || "Sem motoboy"} • {corrida.empresa}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Map Canvas */}
              <div className="flex-1 bg-zinc-100 relative min-h-0">
                <ErrorBoundary>
                  <MapContainer
                    center={originLatLon}
                    zoom={13}
                    style={{ width: "100%", height: "100%" }}
                    zoomControl={false}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    {routeCoordinates.length > 0 && (
                      <>
                        <Polyline
                          positions={routeCoordinates}
                          color="#4f46e5"
                          weight={5}
                          opacity={0.8}
                        />
                        <MapBounds routeCoordinates={routeCoordinates} />
                      </>
                    )}
                    <Marker position={originLatLon} icon={storeIcon}>
                      <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                        Loja (Coleta)
                      </Tooltip>
                    </Marker>
                    <Marker position={destLatLon} icon={dropoffIcon}>
                      <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                        Entrega
                      </Tooltip>
                    </Marker>
                  </MapContainer>
                </ErrorBoundary>

                {isLoadingRoute && (
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-xs px-4 py-2 rounded-xl shadow-md text-xs font-bold text-zinc-800 z-[1000] border border-zinc-200">
                    Calculando rota...
                  </div>
                )}
                {routeError && (
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-rose-50 text-rose-700 px-4 py-2 rounded-xl shadow-md text-xs font-bold z-[1000] border border-rose-200">
                    {routeError}
                  </div>
                )}
              </div>

              {/* Standard Footer */}
              <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
                <div className="grid grid-cols-3 gap-6 text-xs">
                  <div>
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                      Distância
                    </span>
                    <span className="text-sm font-black text-zinc-900">
                      {corrida.distancia || "—"}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                      Status
                    </span>
                    <span
                      className={`inline-flex items-center text-xs font-bold ${
                        corrida.status === "Em andamento"
                          ? "text-blue-600"
                          : corrida.status === "Coletando"
                            ? "text-amber-600"
                            : corrida.status === "Concluída"
                              ? "text-emerald-600"
                              : "text-rose-600"
                      }`}
                    >
                      {corrida.status}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                      Horário
                    </span>
                    <span className="text-sm font-bold text-zinc-900">
                      {corrida.horario || "—"}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={onClose}
                  className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold rounded-xl transition-all cursor-pointer shadow-sm"
                >
                  Fechar
                </button>
              </div>
            </motion.div>
          </div>
        </AnimatePresence>,
        document.body
      )
    : null;
}
