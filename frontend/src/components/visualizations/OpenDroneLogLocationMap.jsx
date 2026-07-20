import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { IconLayer, PathLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import MapLibreMap, {
  FullscreenControl,
  NavigationControl,
  Popup,
  ScaleControl,
  useControl,
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import {
  formatVisualizationDateTime,
  getLocationArray,
  isValidCoordinate,
} from "../../utils/visualizationHelpers";
import {
  OPEN_DRONELOG_MAP_STYLES,
  DEFAULT_OPEN_DRONELOG_MAP_STYLE,
} from "../../utils/openDroneLogMapStyles";

const DEFAULT_CENTER = {
  longitude: 80.9462,
  latitude: 26.8467,
  zoom: 8,
};

const START_NODE_COLOR = "#16a34a";
const END_NODE_COLOR = "#dc2626";
const NORMAL_NODE_COLOR = "#2563eb";
const PATH_COLOR = [37, 99, 235, 190];
const CLUSTER_ICON_WIDTH = 96;
const CLUSTER_ICON_HEIGHT = 96;

function DeckGLOverlay(props) {
  const overlay = useControl(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function cleanText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
}

function formatCoordinate(latitude, longitude) {
  if (!isValidCoordinate(latitude, longitude)) {
    return "Not available";
  }

  return `${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)}`;
}

function formatDuration(seconds) {
  const totalSeconds = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = Math.floor(totalSeconds % 60);

  const parts = [];

  if (hours > 0) {
    parts.push(`${hours}h`);
  }

  if (minutes > 0) {
    parts.push(`${minutes}m`);
  }

  parts.push(`${remainingSeconds}s`);

  return parts.join(" ");
}

function pointKey(cellId, latitude, longitude) {
  const cellPart = cleanText(cellId) || "UNKNOWN-CGI";
  return `${cellPart}|${Number(latitude).toFixed(5)}|${Number(longitude).toFixed(5)}`;
}

function transitionKey(sourceKey, targetKey) {
  return [sourceKey, targetKey].sort().join("<->");
}

function normaliseRecords(result) {
  return getLocationArray(result)
    .map((item, index) => {
      const firstLatitude = toNumber(
        item.first_latitude ?? item.latitude ?? item.lat,
      );
      const firstLongitude = toNumber(
        item.first_longitude ?? item.longitude ?? item.lng ?? item.lon,
      );
      const lastLatitude = toNumber(
        item.last_latitude ?? item.latitude ?? item.first_latitude,
      );
      const lastLongitude = toNumber(
        item.last_longitude ?? item.longitude ?? item.first_longitude,
      );

      const firstCellId = cleanText(
        item.first_cell_global_id ??
          item.cell_id ??
          item.cellId ??
          item.tower_id,
      );

      const lastCellId = cleanText(
        item.last_cell_global_id ??
          item.last_cell_id ??
          item.cell_id ??
          item.cellId ??
          item.tower_id,
      );

      const activityTime =
        item.start_datetime ??
        item.activity_datetime ??
        item.event_datetime ??
        item.first_seen ??
        null;

      return {
        ...item,
        originalIndex: index,
        firstLatitude,
        firstLongitude,
        lastLatitude,
        lastLongitude,
        firstCellId,
        lastCellId,
        targetNumber: cleanText(
          item.target_number ?? item.phone_number ?? result?.phone_number,
        ),
        bPartyNumber: cleanText(item.b_party_number ?? item.contact_number),
        callType: cleanText(item.call_type ?? item.direction),
        communicationType: cleanText(
          item.connection_type ?? item.event_type ?? item.service_type,
        ),
        durationSeconds: Number(item.duration_seconds) || 0,
        sourceRow:
          item.source_row ?? item.sourceRow ?? item.record_id ?? index + 1,
        activityTime,
        timestamp: activityTime ? new Date(activityTime).getTime() : index,
      };
    })
    .filter(
      (record) =>
        isValidCoordinate(record.firstLatitude, record.firstLongitude) ||
        isValidCoordinate(record.lastLatitude, record.lastLongitude),
    )
    .sort((first, second) => {
      const firstTimestamp = Number.isFinite(first.timestamp)
        ? first.timestamp
        : first.originalIndex;
      const secondTimestamp = Number.isFinite(second.timestamp)
        ? second.timestamp
        : second.originalIndex;

      return firstTimestamp - secondTimestamp;
    });
}

function buildMapData(records) {
  const nodeMap = new Map();
  const transitionMap = new Map();

  function addNode({ cellId, latitude, longitude, record, pointType }) {
    if (!isValidCoordinate(latitude, longitude)) {
      return null;
    }

    const key = pointKey(cellId, latitude, longitude);
    const current = nodeMap.get(key) ?? {
      id: key,
      cellId: cellId || "Unknown CGI",
      longitude: Number(longitude),
      latitude: Number(latitude),
      recordCount: 0,
      recordKeys: new Set(),
      sourceRows: new Set(),
      firstSourceRows: new Set(),
      lastSourceRows: new Set(),
      firstPointCount: 0,
      lastPointCount: 0,
      firstSeen: record.activityTime,
      lastSeen: record.activityTime,
      targetNumbers: new Set(),
      bPartyNumbers: new Set(),
      callTypes: new Set(),
      communicationTypes: new Set(),
      totalDurationSeconds: 0,
      sampleRecord: record,
      records: [],
    };

    const recordKey = String(
      record.record_id ?? record.source_row ?? record.originalIndex,
    );

    if (!current.recordKeys.has(recordKey)) {
      current.recordKeys.add(recordKey);
      current.recordCount += 1;
      current.totalDurationSeconds += record.durationSeconds;
      current.sourceRows.add(String(record.sourceRow));
      current.records.push(record);

      if (record.targetNumber) {
        current.targetNumbers.add(record.targetNumber);
      }

      if (record.bPartyNumber) {
        current.bPartyNumbers.add(record.bPartyNumber);
      }

      if (record.callType) {
        current.callTypes.add(record.callType);
      }

      if (record.communicationType) {
        current.communicationTypes.add(record.communicationType);
      }
    }

    if (pointType === "first") {
      current.firstPointCount += 1;
      current.firstSourceRows.add(String(record.sourceRow));
    } else {
      current.lastPointCount += 1;
      current.lastSourceRows.add(String(record.sourceRow));
    }

    if (
      record.activityTime &&
      (!current.firstSeen ||
        new Date(record.activityTime) < new Date(current.firstSeen))
    ) {
      current.firstSeen = record.activityTime;
    }

    if (
      record.activityTime &&
      (!current.lastSeen ||
        new Date(record.activityTime) > new Date(current.lastSeen))
    ) {
      current.lastSeen = record.activityTime;
    }

    nodeMap.set(key, current);
    return key;
  }

  records.forEach((record) => {
    const sourceKey = addNode({
      cellId: record.firstCellId,
      latitude: record.firstLatitude,
      longitude: record.firstLongitude,
      record,
      pointType: "first",
    });

    const targetKey = addNode({
      cellId: record.lastCellId,
      latitude: record.lastLatitude,
      longitude: record.lastLongitude,
      record,
      pointType: "last",
    });

    if (!sourceKey || !targetKey || sourceKey === targetKey) {
      return;
    }

    const sourceNode = nodeMap.get(sourceKey);
    const targetNode = nodeMap.get(targetKey);
    const key = transitionKey(sourceKey, targetKey);

    const current = transitionMap.get(key) ?? {
      id: key,
      sourceKey,
      targetKey,
      sourceCellId: sourceNode.cellId,
      targetCellId: targetNode.cellId,
      path: [
        [sourceNode.longitude, sourceNode.latitude],
        [targetNode.longitude, targetNode.latitude],
      ],
      recordCount: 0,
      sourceRows: new Set(),
      firstSeen: record.activityTime,
      lastSeen: record.activityTime,
      callTypes: new Set(),
      communicationTypes: new Set(),
      totalDurationSeconds: 0,
    };

    current.recordCount += 1;
    current.totalDurationSeconds += record.durationSeconds;
    current.sourceRows.add(String(record.sourceRow));

    if (record.callType) {
      current.callTypes.add(record.callType);
    }

    if (record.communicationType) {
      current.communicationTypes.add(record.communicationType);
    }

    if (
      record.activityTime &&
      (!current.firstSeen ||
        new Date(record.activityTime) < new Date(current.firstSeen))
    ) {
      current.firstSeen = record.activityTime;
    }

    if (
      record.activityTime &&
      (!current.lastSeen ||
        new Date(record.activityTime) > new Date(current.lastSeen))
    ) {
      current.lastSeen = record.activityTime;
    }

    transitionMap.set(key, current);
  });

  const nodes = Array.from(nodeMap.values()).map((node) => {
    const { recordKeys, ...serializableNode } = node;

    return {
      ...serializableNode,
      sourceRows: Array.from(node.sourceRows).sort(
        (first, second) => Number(first) - Number(second),
      ),
      firstSourceRows: Array.from(node.firstSourceRows).sort(
        (first, second) => Number(first) - Number(second),
      ),
      lastSourceRows: Array.from(node.lastSourceRows).sort(
        (first, second) => Number(first) - Number(second),
      ),
      targetNumbers: Array.from(node.targetNumbers).sort(),
      bPartyNumbers: Array.from(node.bPartyNumbers).sort(),
      callTypes: Array.from(node.callTypes).sort(),
      communicationTypes: Array.from(node.communicationTypes).sort(),
      records: [...node.records].sort((first, second) => {
        const firstTimestamp = Number.isFinite(first.timestamp)
          ? first.timestamp
          : first.originalIndex;
        const secondTimestamp = Number.isFinite(second.timestamp)
          ? second.timestamp
          : second.originalIndex;

        return firstTimestamp - secondTimestamp;
      }),
    };
  });

  const transitions = Array.from(transitionMap.values()).map((transition) => ({
    ...transition,
    sourceRows: Array.from(transition.sourceRows).sort(
      (first, second) => Number(first) - Number(second),
    ),
    callTypes: Array.from(transition.callTypes).sort(),
    communicationTypes: Array.from(transition.communicationTypes).sort(),
  }));

  const firstRecord = records[0] ?? null;
  const lastRecord = records[records.length - 1] ?? null;

  const startNodeId =
    firstRecord &&
    isValidCoordinate(firstRecord.firstLatitude, firstRecord.firstLongitude)
      ? pointKey(
          firstRecord.firstCellId,
          firstRecord.firstLatitude,
          firstRecord.firstLongitude,
        )
      : null;

  const endNodeId =
    lastRecord &&
    isValidCoordinate(lastRecord.lastLatitude, lastRecord.lastLongitude)
      ? pointKey(
          lastRecord.lastCellId,
          lastRecord.lastLatitude,
          lastRecord.lastLongitude,
        )
      : null;

  return {
    nodes,
    transitions,
    startNodeId,
    endNodeId,
  };
}

function calculateBounds(nodes) {
  if (!nodes.length) {
    return null;
  }

  const longitudes = nodes.map((node) => node.longitude);
  const latitudes = nodes.map((node) => node.latitude);

  return [
    [Math.min(...longitudes), Math.min(...latitudes)],
    [Math.max(...longitudes), Math.max(...latitudes)],
  ];
}

function clusterCountLabel(recordCount) {
  const count = Math.max(0, Number(recordCount) || 0);

  if (count > 999) {
    return "999+";
  }

  return String(count);
}

function clusterMarkerSize(recordCount) {
  const count = Math.max(1, Number(recordCount) || 1);

  if (count >= 50) {
    return 68;
  }

  if (count >= 20) {
    return 62;
  }

  if (count >= 10) {
    return 58;
  }

  if (count >= 5) {
    return 54;
  }

  if (count >= 2) {
    return 50;
  }

  return 44;
}

function nodeMarkerColor(node, startNodeId, endNodeId) {
  if (node.id === startNodeId) {
    return START_NODE_COLOR;
  }

  if (node.id === endNodeId) {
    return END_NODE_COLOR;
  }

  return NORMAL_NODE_COLOR;
}

function createClusterMarkerSvg({ color, recordCount }) {
  const label = clusterCountLabel(recordCount);
  const isCluster = Number(recordCount) > 1;

  const backLayers = isCluster
    ? `
      <circle cx="34" cy="48" r="24" fill="${color}" fill-opacity="0.28"/>
      <circle cx="42" cy="48" r="24" fill="${color}" fill-opacity="0.52"/>
    `
    : "";

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${CLUSTER_ICON_WIDTH}" height="${CLUSTER_ICON_HEIGHT}" viewBox="0 0 96 96">
      <defs>
        <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.28"/>
        </filter>
      </defs>
      <g filter="url(#shadow)">
        ${backLayers}
        <circle cx="50" cy="48" r="25" fill="${color}" stroke="#ffffff" stroke-width="4"/>
      </g>
      <text
        x="50"
        y="54"
        text-anchor="middle"
        font-family="Inter, Arial, sans-serif"
        font-size="${label.length > 3 ? 15 : 18}"
        font-weight="800"
        fill="#ffffff"
      >${label}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function clusterIconDefinition(node, startNodeId, endNodeId) {
  return {
    url: createClusterMarkerSvg({
      color: nodeMarkerColor(node, startNodeId, endNodeId),
      recordCount: node.recordCount,
    }),
    width: CLUSTER_ICON_WIDTH,
    height: CLUSTER_ICON_HEIGHT,
    anchorX: CLUSTER_ICON_WIDTH / 2,
    anchorY: CLUSTER_ICON_HEIGHT / 2,
    mask: false,
  };
}

function compactSourceRowList(sourceRows, limit = 6) {
  if (!Array.isArray(sourceRows) || sourceRows.length === 0) {
    return "Not available";
  }

  const visibleRows = sourceRows.slice(0, limit);
  const remaining = sourceRows.length - visibleRows.length;

  return remaining > 0
    ? `${visibleRows.join(", ")} +${remaining} more`
    : visibleRows.join(", ");
}

function sourceRowList(sourceRows) {
  if (!Array.isArray(sourceRows) || sourceRows.length === 0) {
    return "Not available";
  }

  return sourceRows.join(", ");
}

function PopupRow({ label, value }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-3 py-1.5 text-xs">
      <span className="font-semibold text-slate-500">{label}</span>
      <span className="break-words text-slate-900">
        {value || "Not available"}
      </span>
    </div>
  );
}

function NodeRecordCard({ record }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-bold text-blue-700">
          Source row {record.sourceRow}
        </p>

        <p className="text-[11px] font-medium text-slate-500">
          {formatVisualizationDateTime(record.activityTime)}
        </p>
      </div>

      <div className="mt-2 grid gap-x-4 gap-y-1 text-[11px] sm:grid-cols-2">
        <p>
          <span className="font-semibold text-slate-500">PAN:</span>{" "}
          <span className="text-slate-900">
            {cleanText(record.pan_no) || "Not available"}
          </span>
        </p>

        <p>
          <span className="font-semibold text-slate-500">Target:</span>{" "}
          <span className="text-slate-900">
            {record.targetNumber || "Not available"}
          </span>
        </p>

        <p>
          <span className="font-semibold text-slate-500">B-party:</span>{" "}
          <span className="text-slate-900">
            {record.bPartyNumber || "Not available"}
          </span>
        </p>

        <p>
          <span className="font-semibold text-slate-500">Call type:</span>{" "}
          <span className="text-slate-900">
            {record.callType || "Not available"}
          </span>
        </p>

        <p>
          <span className="font-semibold text-slate-500">TOC:</span>{" "}
          <span className="text-slate-900">
            {record.communicationType || "Not available"}
          </span>
        </p>

        <p>
          <span className="font-semibold text-slate-500">Duration:</span>{" "}
          <span className="text-slate-900">
            {formatDuration(record.durationSeconds)}
          </span>
        </p>

        <p className="sm:col-span-2">
          <span className="font-semibold text-slate-500">CGI movement:</span>{" "}
          <span className="text-slate-900">
            {record.firstCellId || "Unknown CGI"} →{" "}
            {record.lastCellId || "Unknown CGI"}
          </span>
        </p>
      </div>
    </article>
  );
}

export default function OpenDroneLogLocationMap({
  result,
  showMovementPath = true,
}) {
  const mapRef = useRef(null);
  const [mapType, setMapType] = useState(DEFAULT_OPEN_DRONELOG_MAP_STYLE);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [hoveredFeature, setHoveredFeature] = useState(null);

  const records = useMemo(() => normaliseRecords(result), [result]);
  const mapData = useMemo(() => buildMapData(records), [records]);
  const bounds = useMemo(() => calculateBounds(mapData.nodes), [mapData.nodes]);

  const fitMapToData = useCallback(
    (duration = 0) => {
      const map = mapRef.current;

      if (!map || !bounds) {
        return;
      }

      const [southWest, northEast] = bounds;
      const samePoint =
        southWest[0] === northEast[0] && southWest[1] === northEast[1];

      if (samePoint) {
        map.flyTo({
          center: southWest,
          zoom: 14,
          pitch: 0,
          bearing: 0,
          duration,
        });
        return;
      }

      map.fitBounds(bounds, {
        padding: {
          top: 70,
          right: 70,
          bottom: 70,
          left: 70,
        },
        maxZoom: 15,
        pitch: 0,
        bearing: 0,
        duration,
      });
    },
    [bounds],
  );

  useEffect(() => {
    if (!mapRef.current || !bounds) {
      return;
    }

    const timer = window.setTimeout(() => {
      fitMapToData(650);
    }, 150);

    return () => window.clearTimeout(timer);
  }, [fitMapToData, bounds, mapType]);

  const layers = useMemo(() => {
    const generatedLayers = [];

    if (showMovementPath && mapData.transitions.length > 0) {
      generatedLayers.push(
        new PathLayer({
          id: "cdr-cgi-transitions",
          data: mapData.transitions,
          pickable: true,
          autoHighlight: true,
          highlightColor: [15, 23, 42, 80],
          getPath: (transition) => transition.path,
          getColor: PATH_COLOR,
          getWidth: (transition) =>
            Math.min(8, 2.2 + Math.log2(transition.recordCount + 1) * 1.4),
          widthUnits: "pixels",
          widthMinPixels: 2,
          capRounded: true,
          jointRounded: true,
          opacity: 0.86,
          parameters: {
            depthTest: false,
          },
          onHover: (info) => {
            setHoveredFeature(
              info.object
                ? {
                    kind: "transition",
                    object: info.object,
                    x: info.x,
                    y: info.y,
                  }
                : null,
            );
          },
          onClick: (info) => {
            if (!info.object || !info.coordinate) {
              return;
            }

            setSelectedFeature({
              kind: "transition",
              object: info.object,
              longitude: info.coordinate[0],
              latitude: info.coordinate[1],
            });
          },
        }),
      );
    }

    const markerNodes = mapData.nodes.map((node) => ({
      ...node,
      markerIcon: clusterIconDefinition(
        node,
        mapData.startNodeId,
        mapData.endNodeId,
      ),
    }));

    generatedLayers.push(
      new IconLayer({
        id: "cdr-cgi-cluster-markers",
        data: markerNodes,
        pickable: true,
        autoHighlight: true,
        highlightColor: [255, 255, 255, 90],
        getPosition: (node) => [node.longitude, node.latitude],
        getIcon: (node) => node.markerIcon,
        getSize: (node) => clusterMarkerSize(node.recordCount),
        sizeUnits: "pixels",
        alphaCutoff: 0.03,
        billboard: true,
        parameters: {
          depthTest: false,
        },
        onHover: (info) => {
          setHoveredFeature(
            info.object
              ? {
                  kind: "node",
                  object: info.object,
                  x: info.x,
                  y: info.y,
                }
              : null,
          );
        },
        onClick: (info) => {
          if (!info.object) {
            return;
          }

          setSelectedFeature({
            kind: "node",
            object: info.object,
            longitude: info.object.longitude,
            latitude: info.object.latitude,
          });
        },
      }),
    );

    return generatedLayers;
  }, [mapData, showMovementPath]);

  const selectedMapStyle =
    OPEN_DRONELOG_MAP_STYLES[mapType] ??
    OPEN_DRONELOG_MAP_STYLES[DEFAULT_OPEN_DRONELOG_MAP_STYLE];

  if (mapData.nodes.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <h3 className="font-bold text-slate-900">
          No valid coordinates available
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          The selected result has no usable FIRST_CGI or LAST_CGI coordinates.
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 p-5">
        <div>
          <h2 className="text-lg font-bold text-slate-950">
            Open DroneLog-style CGI movement map
          </h2>

          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Each round marker represents one CGI location. The number inside is
            the count of history-table entries at that tower. Click a marker to
            view every source-row entry associated with the location.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={mapType}
            onChange={(event) => setMapType(event.target.value)}
            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none focus:border-blue-500"
            aria-label="Select map type"
          >
            {Object.entries(OPEN_DRONELOG_MAP_STYLES).map(([key, value]) => (
              <option key={key} value={key}>
                {value.label}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => fitMapToData(550)}
            className="rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            Fit locations
          </button>
        </div>
      </div>

      <div className="relative h-[560px] w-full border-y border-slate-200 bg-slate-100">
        <MapLibreMap
          ref={mapRef}
          initialViewState={{
            ...DEFAULT_CENTER,
            pitch: 0,
            bearing: 0,
          }}
          mapStyle={selectedMapStyle.style}
          style={{ width: "100%", height: "100%" }}
          maxPitch={0}
          dragRotate={false}
          touchPitch={false}
          attributionControl
          antialias
          onLoad={() => fitMapToData(0)}
        >
          <DeckGLOverlay
            layers={layers}
            interleaved
            getCursor={({ isHovering, isDragging }) => {
              if (isDragging) {
                return "grabbing";
              }

              return isHovering ? "pointer" : "grab";
            }}
          />

          <NavigationControl position="top-left" showCompass={false} />
          <FullscreenControl position="top-left" />
          <ScaleControl position="bottom-left" unit="metric" />

          {selectedFeature?.kind === "node" && (
            <Popup
              longitude={selectedFeature.longitude}
              latitude={selectedFeature.latitude}
              anchor="bottom"
              closeOnClick={false}
              closeButton
              maxWidth="560px"
              onClose={() => setSelectedFeature(null)}
            >
              <div className="min-w-[440px] p-1">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-950">
                      {selectedFeature.object.cellId}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">
                      {selectedFeature.object.recordCount} history-table{" "}
                      {selectedFeature.object.recordCount === 1
                        ? "entry"
                        : "entries"}{" "}
                      at this CGI location
                    </p>
                  </div>

                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
                    {selectedFeature.object.recordCount} entries
                  </span>
                </div>

                <div className="mt-3 divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white px-3">
                  <PopupRow
                    label="Coordinates"
                    value={formatCoordinate(
                      selectedFeature.object.latitude,
                      selectedFeature.object.longitude,
                    )}
                  />
                  <PopupRow
                    label="Source rows"
                    value={sourceRowList(selectedFeature.object.sourceRows)}
                  />
                  <PopupRow
                    label="First seen"
                    value={formatVisualizationDateTime(
                      selectedFeature.object.firstSeen,
                    )}
                  />
                  <PopupRow
                    label="Last seen"
                    value={formatVisualizationDateTime(
                      selectedFeature.object.lastSeen,
                    )}
                  />
                </div>

                <div className="mt-4">
                  <h4 className="text-xs font-bold uppercase tracking-wide text-slate-600">
                    Entries at this location
                  </h4>

                  <div className="mt-2 max-h-72 space-y-2 overflow-y-auto pr-1">
                    {selectedFeature.object.records.map((record) => (
                      <NodeRecordCard
                        key={`${record.record_id ?? record.sourceRow}-${record.originalIndex}`}
                        record={record}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </Popup>
          )}

          {selectedFeature?.kind === "transition" && (
            <Popup
              longitude={selectedFeature.longitude}
              latitude={selectedFeature.latitude}
              anchor="bottom"
              closeOnClick={false}
              closeButton
              maxWidth="360px"
              onClose={() => setSelectedFeature(null)}
            >
              <div className="min-w-[300px] p-1">
                <h3 className="text-sm font-bold text-slate-950">
                  CGI transition
                </h3>

                <div className="mt-2 divide-y divide-slate-100">
                  <PopupRow
                    label="From"
                    value={selectedFeature.object.sourceCellId}
                  />
                  <PopupRow
                    label="To"
                    value={selectedFeature.object.targetCellId}
                  />
                  <PopupRow
                    label="Source rows"
                    value={sourceRowList(selectedFeature.object.sourceRows)}
                  />
                  <PopupRow
                    label="Call types"
                    value={selectedFeature.object.callTypes.join(", ")}
                  />
                  <PopupRow
                    label="TOC"
                    value={selectedFeature.object.communicationTypes.join(", ")}
                  />
                  <PopupRow
                    label="Total duration"
                    value={formatDuration(
                      selectedFeature.object.totalDurationSeconds,
                    )}
                  />
                  <PopupRow
                    label="First seen"
                    value={formatVisualizationDateTime(
                      selectedFeature.object.firstSeen,
                    )}
                  />
                  <PopupRow
                    label="Last seen"
                    value={formatVisualizationDateTime(
                      selectedFeature.object.lastSeen,
                    )}
                  />
                </div>
              </div>
            </Popup>
          )}
        </MapLibreMap>

        {hoveredFeature && (
          <div
            className="pointer-events-none absolute z-20 w-64 rounded-xl border border-slate-200 bg-white/95 p-3 shadow-xl backdrop-blur"
            style={{
              left: Math.min(hoveredFeature.x + 14, 760),
              top: Math.max(12, hoveredFeature.y - 20),
            }}
          >
            {hoveredFeature.kind === "node" ? (
              <>
                <p className="text-sm font-bold text-slate-950">
                  {hoveredFeature.object.cellId}
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  {hoveredFeature.object.recordCount}{" "}
                  {hoveredFeature.object.recordCount === 1
                    ? "entry"
                    : "entries"}{" "}
                  at this location
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Source rows:{" "}
                  {compactSourceRowList(hoveredFeature.object.sourceRows)}
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-bold text-slate-950">
                  {hoveredFeature.object.sourceCellId} →{" "}
                  {hoveredFeature.object.targetCellId}
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  Source rows: {sourceRowList(hoveredFeature.object.sourceRows)}
                </p>
              </>
            )}
          </div>
        )}

        <div className="pointer-events-none absolute bottom-4 right-4 z-10 rounded-xl border border-white/70 bg-white/90 px-3 py-2 text-xs font-semibold text-slate-700 shadow-lg backdrop-blur">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-green-600" />
              First recorded CGI
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-600" />
              Last recorded CGI
            </span>
            <span className="flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-[9px] font-bold text-white">
                #
              </span>
              Number = entries at CGI
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-0.5 w-5 bg-blue-600" />
              Aggregated handover
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4 text-sm sm:grid-cols-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Unique CGI points
          </p>
          <p className="mt-1 text-lg font-bold text-slate-950">
            {mapData.nodes.length}
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Unique handover pairs
          </p>
          <p className="mt-1 text-lg font-bold text-slate-950">
            {mapData.transitions.length}
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Location records analysed
          </p>
          <p className="mt-1 text-lg font-bold text-slate-950">
            {records.length}
          </p>
        </div>
      </div>

      <div className="p-4 text-xs leading-5 text-slate-500">
        This 2D CDR map uses the React Map GL, MapLibre and Deck.gl mapping
        approach documented by Open DroneLog. CGI coordinates represent
        serving-cell locations and indicate an approximate network area; they
        are not precise GPS proof of a person’s physical position.
      </div>
    </section>
  );
}
