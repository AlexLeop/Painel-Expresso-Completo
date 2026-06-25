import React, { useState, useEffect, useRef, useCallback } from "react";
import { MapPin, Loader2, Search } from "lucide-react";
import { cn } from "../lib/utils";

interface NominatimResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  address: {
    road?: string;
    house_number?: string;
    suburb?: string;
    city?: string;
    state?: string;
    postcode?: string;
    country?: string;
  };
}

interface AddressAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (result: NominatimResult) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
  id?: string;
  /** Country code to bias results (default: "br") */
  countryCode?: string;
  /** City to bias results (e.g., "São Paulo") */
  cityBias?: string;
}

const DEBOUNCE_MS = 350;
const MIN_CHARS = 4;

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  placeholder = "Rua, Avenida...",
  required,
  className,
  id,
  countryCode = "br",
  cityBias,
}: AddressAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<NominatimResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const debouncedQuery = useDebounce(value, DEBOUNCE_MS);

  const fetchSuggestions = useCallback(async (query: string) => {
    if (query.length < MIN_CHARS) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    // Abort previous request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        q: cityBias ? `${query}, ${cityBias}` : query,
        format: "json",
        addressdetails: "1",
        limit: "6",
        countrycodes: countryCode,
        "accept-language": "pt-BR",
      });

      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?${params.toString()}`,
        {
          signal: abortRef.current.signal,
          headers: { "User-Agent": "ExpressoNeves-Painel/1.0" },
        }
      );

      if (!res.ok) throw new Error("Nominatim error");
      const data: NominatimResult[] = await res.json();
      setSuggestions(data);
      setIsOpen(data.length > 0);
      setActiveIndex(-1);
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setSuggestions([]);
        setIsOpen(false);
      }
    } finally {
      setIsLoading(false);
    }
  }, [countryCode, cityBias]);

  useEffect(() => {
    fetchSuggestions(debouncedQuery);
  }, [debouncedQuery, fetchSuggestions]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(result: NominatimResult) {
    // Build a clean address string
    const addr = result.address;
    const parts = [
      addr.road,
      addr.house_number,
      addr.suburb,
      addr.city,
      addr.state,
    ].filter(Boolean);
    const clean = parts.length > 0 ? parts.join(", ") : result.display_name.split(",").slice(0, 3).join(",");

    onChange(clean);
    onSelect?.(result);
    setIsOpen(false);
    setSuggestions([]);
    inputRef.current?.blur();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!isOpen || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex(i => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex(i => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[activeIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  }

  // Format display name to be compact
  function formatDisplay(result: NominatimResult): { main: string; sub: string } {
    const parts = result.display_name.split(", ");
    return {
      main: parts.slice(0, 2).join(", "),
      sub: parts.slice(2, 5).join(", "),
    };
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-emerald-500 pointer-events-none z-10" />
        <input
          ref={inputRef}
          id={id}
          type="text"
          value={value}
          required={required}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          autoComplete="off"
          className={cn(
            "w-full pl-9 pr-8 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all",
            className
          )}
        />
        {isLoading && (
          <Loader2 className="absolute right-2.5 top-2.5 h-4 w-4 text-zinc-400 animate-spin pointer-events-none" />
        )}
        {!isLoading && value.length >= MIN_CHARS && !isOpen && (
          <Search className="absolute right-2.5 top-2.5 h-4 w-4 text-zinc-300 pointer-events-none" />
        )}
      </div>

      {isOpen && suggestions.length > 0 && (
        <div className="absolute z-[9999] w-full mt-1 bg-white border border-zinc-200 rounded-xl shadow-xl overflow-hidden">
          <div className="px-3 py-1.5 border-b border-zinc-100 flex items-center gap-1.5">
            <Search className="h-3 w-3 text-zinc-400" />
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
              Sugestões de endereço
            </span>
          </div>
          <ul role="listbox" className="max-h-64 overflow-y-auto">
            {suggestions.map((result, index) => {
              const { main, sub } = formatDisplay(result);
              return (
                <li
                  key={result.place_id}
                  role="option"
                  aria-selected={index === activeIndex}
                  onMouseDown={(e) => { e.preventDefault(); handleSelect(result); }}
                  onMouseEnter={() => setActiveIndex(index)}
                  className={cn(
                    "flex items-start gap-3 px-3 py-2.5 cursor-pointer transition-colors",
                    index === activeIndex ? "bg-zinc-100" : "hover:bg-zinc-50"
                  )}
                >
                  <div className="mt-0.5 shrink-0 w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center">
                    <MapPin className="h-3 w-3 text-emerald-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-zinc-900 truncate">{main}</p>
                    {sub && <p className="text-[11px] text-zinc-500 truncate">{sub}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="px-3 py-1.5 border-t border-zinc-100 bg-zinc-50">
            <span className="text-[9px] text-zinc-400">Dados: OpenStreetMap · Nominatim</span>
          </div>
        </div>
      )}
    </div>
  );
}
