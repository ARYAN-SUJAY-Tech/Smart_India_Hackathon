"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip, ZoomControl, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { RISK_LEVEL_META } from "@/lib/riskLevels";
import type { VillageRisk } from "@/lib/types";

// Centered on Backend/seed_data.py's sample villages (30.28-30.35N, 78.03-78.10E,
// Uttarakhand hills) -- swap once real village coordinates are seeded.
export const DEFAULT_CENTER: [number, number] = [30.32, 78.07];
export const DEFAULT_ZOOM = 12;

function MapController({ activeVillage }: { activeVillage: VillageRisk | null }) {
  const map = useMap();

  useEffect(() => {
    if (activeVillage) {
      map.flyTo([activeVillage.latitude, activeVillage.longitude], 14, {
        duration: 1.5,
        easeLinearity: 0.25,
      });
    }
  }, [activeVillage, map]);

  return null;
}

interface MapWidgetProps {
  villages: VillageRisk[];
  activeVillage: VillageRisk | null;
  onSelectVillage: (village: VillageRisk) => void;
  center?: [number, number];
  zoom?: number;
}

export default function MapWidget({
  villages,
  activeVillage,
  onSelectVillage,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
}: MapWidgetProps) {
  return (
    <div className="absolute inset-0 w-full h-full bg-black z-0">
      <MapContainer
        center={center}
        zoom={zoom}
        zoomControl={false}
        style={{ height: "100%", width: "100%", background: "transparent" }}
        attributionControl={false}
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri"
          maxZoom={16}
        />

        {/* bottom-left, not bottom-right -- the village detail drawer slides
            in from the right and would otherwise cover the controls */}
        <ZoomControl position="bottomleft" />

        <MapController activeVillage={activeVillage} />

        {villages.map((village) => {
          const isActive = activeVillage?.id === village.id;
          const color = RISK_LEVEL_META[village.risk_level].color;
          return (
            <CircleMarker
              key={village.id}
              center={[village.latitude, village.longitude]}
              radius={isActive ? 14 : 9}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: isActive ? 0.9 : 0.6,
                weight: isActive ? 3 : 1.5,
              }}
              eventHandlers={{
                click: () => onSelectVillage(village),
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1} permanent={isActive}>
                <span className="text-xs font-medium">{village.name}</span>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
