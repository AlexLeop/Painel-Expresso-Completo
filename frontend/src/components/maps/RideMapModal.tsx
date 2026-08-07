import { logger } from "@/lib/logger";
import React, { useEffect, useState } from "react";
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

  return (
    <div className="fixed inset-0 z-[60] bg-gray-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-xl overflow-hidden flex flex-col h-[80vh]">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-50 rounded-lg">
              <MapIcon className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 leading-none">
                Rota da Corrida #{corrida.id}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {motoboyName || "Sem motoboy"} • {corrida.empresa}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 bg-gray-100 relative">
          <ErrorBoundary>
            <MapContainer
              center={originLatLon}
              zoom={13}
              style={{ width: "100%", height: "100%" }}
              zoomControl={false}
            >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
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
            <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-white px-4 py-2 rounded-lg shadow-md text-sm font-medium text-gray-700 z-[1000]">
              Calculando rota...
            </div>
          )}
          {routeError && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-rose-100 text-rose-700 px-4 py-2 rounded-lg shadow-md text-sm font-medium z-[1000]">
              {routeError}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 bg-gray-50 grid grid-cols-3 gap-4">
          <div>
            <span className="block text-xs font-medium text-gray-500 uppercase">
              Distância Estimada
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {corrida.distancia}
            </span>
          </div>
          <div>
            <span className="block text-xs font-medium text-gray-500 uppercase">
              Status
            </span>
            <span
              className={`inline-flex items-center text-sm font-semibold ${
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
            <span className="block text-xs font-medium text-gray-500 uppercase">
              Horário de Saída
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {corrida.horario}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
