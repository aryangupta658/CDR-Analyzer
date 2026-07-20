import {
  ChevronDown,
  ChevronUp,
  Network,
  Phone,
  RotateCcw,
  Users,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { useMemo, useState } from "react";

import { formatVisualizationDuration } from "../../utils/visualizationHelpers";

const WIDTH = 1450;
const HEIGHT = 920;

function hashText(value) {
  let hash = 0;

  for (const character of String(value || "")) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }

  return hash;
}

function getNodeRadius(node, maximumRecords) {
  if (node.is_root) {
    return 58;
  }

  const records = Math.max(1, Number(node.total_records) || 1);
  const maximum = Math.max(1, maximumRecords);
  const normalized = Math.log1p(records) / Math.log1p(maximum);

  return 24 + normalized * 22;
}

function getNodeTheme(node) {
  if (node.is_root) {
    return {
      fill: "#2563eb",
      stroke: "#1d4ed8",
      text: "#ffffff",
      halo: "#bfdbfe",
    };
  }

  if (Number(node.depth) === 1) {
    return {
      fill: "#eff6ff",
      stroke: "#60a5fa",
      text: "#1e3a8a",
      halo: "#dbeafe",
    };
  }

  if (Number(node.depth) === 2) {
    return {
      fill: "#f5f3ff",
      stroke: "#8b5cf6",
      text: "#5b21b6",
      halo: "#ede9fe",
    };
  }

  return {
    fill: "#fff7ed",
    stroke: "#f59e0b",
    text: "#92400e",
    halo: "#ffedd5",
  };
}

function buildForceLayout(nodes, edges) {
  const centreX = WIDTH / 2;
  const centreY = HEIGHT / 2;
  const positions = {};
  const velocities = {};

  const depthGroups = nodes.reduce((groups, node) => {
    const depth = Number(node.depth) || 0;

    if (!groups[depth]) {
      groups[depth] = [];
    }

    groups[depth].push(node);
    return groups;
  }, {});

  for (const [depthText, group] of Object.entries(depthGroups)) {
    const depth = Number(depthText);
    const radius =
      depth === 0 ? 0 : depth === 1 ? 230 : depth === 2 ? 390 : 525;

    group.forEach((node, index) => {
      if (node.is_root) {
        positions[node.phone_number] = { x: centreX, y: centreY };
        velocities[node.phone_number] = { x: 0, y: 0 };
        return;
      }

      const seed = hashText(node.phone_number) / 0xffffffff;
      const angle =
        (index / Math.max(group.length, 1)) * Math.PI * 2 + seed * 0.8;
      const radialJitter = (seed - 0.5) * 70;

      positions[node.phone_number] = {
        x: centreX + (radius + radialJitter) * Math.cos(angle),
        y: centreY + (radius + radialJitter) * Math.sin(angle),
      };
      velocities[node.phone_number] = { x: 0, y: 0 };
    });
  }

  const iterations = nodes.length > 100 ? 130 : 220;

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const cooling = 1 - iteration / iterations;
    const forces = Object.fromEntries(
      nodes.map((node) => [node.phone_number, { x: 0, y: 0 }]),
    );

    for (let firstIndex = 0; firstIndex < nodes.length; firstIndex += 1) {
      const firstNode = nodes[firstIndex];
      const first = positions[firstNode.phone_number];

      for (
        let secondIndex = firstIndex + 1;
        secondIndex < nodes.length;
        secondIndex += 1
      ) {
        const secondNode = nodes[secondIndex];
        const second = positions[secondNode.phone_number];
        let dx = first.x - second.x;
        let dy = first.y - second.y;
        let distanceSquared = dx * dx + dy * dy;

        if (distanceSquared < 1) {
          dx = 1;
          dy = 1;
          distanceSquared = 2;
        }

        const distance = Math.sqrt(distanceSquared);
        const repulsion = Math.min(32, 12500 / distanceSquared);
        const forceX = (dx / distance) * repulsion;
        const forceY = (dy / distance) * repulsion;

        forces[firstNode.phone_number].x += forceX;
        forces[firstNode.phone_number].y += forceY;
        forces[secondNode.phone_number].x -= forceX;
        forces[secondNode.phone_number].y -= forceY;
      }
    }

    for (const edge of edges) {
      const source = positions[edge.source];
      const target = positions[edge.target];

      if (!source || !target) {
        continue;
      }

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      const desiredDistance =
        edge.relationship_type === "root_direct" ? 230 : 155;
      const springStrength =
        edge.relationship_type === "root_direct" ? 0.025 : 0.045;
      const displacement = (distance - desiredDistance) * springStrength;
      const forceX = (dx / distance) * displacement;
      const forceY = (dy / distance) * displacement;

      forces[edge.source].x += forceX;
      forces[edge.source].y += forceY;
      forces[edge.target].x -= forceX;
      forces[edge.target].y -= forceY;
    }

    for (const node of nodes) {
      if (node.is_root) {
        positions[node.phone_number] = { x: centreX, y: centreY };
        velocities[node.phone_number] = { x: 0, y: 0 };
        continue;
      }

      const position = positions[node.phone_number];
      const depth = Number(node.depth) || 1;
      const targetRadius = depth === 1 ? 230 : depth === 2 ? 390 : 525;
      const fromCentreX = position.x - centreX;
      const fromCentreY = position.y - centreY;
      const currentRadius = Math.max(
        1,
        Math.sqrt(fromCentreX * fromCentreX + fromCentreY * fromCentreY),
      );
      const ringDifference = targetRadius - currentRadius;

      forces[node.phone_number].x +=
        (fromCentreX / currentRadius) * ringDifference * 0.015;
      forces[node.phone_number].y +=
        (fromCentreY / currentRadius) * ringDifference * 0.015;

      const velocity = velocities[node.phone_number];
      velocity.x = (velocity.x + forces[node.phone_number].x) * 0.82;
      velocity.y = (velocity.y + forces[node.phone_number].y) * 0.82;

      position.x += velocity.x * cooling;
      position.y += velocity.y * cooling;

      position.x = Math.max(70, Math.min(WIDTH - 70, position.x));
      position.y = Math.max(70, Math.min(HEIGHT - 70, position.y));
    }
  }

  return positions;
}

function getCurvePath(source, target, edge) {
  const middleX = (source.x + target.x) / 2;
  const middleY = (source.y + target.y) / 2;
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.max(1, Math.sqrt(dx * dx + dy * dy));
  const bendDirection =
    hashText(`${edge.source}-${edge.target}`) % 2 === 0 ? 1 : -1;
  const bend = edge.relationship_type === "peer_link" ? 24 : 8;
  const controlX = middleX + (-dy / distance) * bend * bendDirection;
  const controlY = middleY + (dx / distance) * bend * bendDirection;

  return {
    path: `M ${source.x} ${source.y} Q ${controlX} ${controlY} ${target.x} ${target.y}`,
    labelX: (middleX + controlX) / 2,
    labelY: (middleY + controlY) / 2,
  };
}

function DetailValue({ label, value }) {
  return (
    <div className="rounded-xl bg-white p-3 ring-1 ring-slate-200">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-1 break-words font-bold text-slate-900">{value}</p>
    </div>
  );
}

export default function MultiLevelContactNetworkGraph({ network }) {
  const [selectedNodeNumber, setSelectedNodeNumber] = useState("");
  const [selectedEdgeKey, setSelectedEdgeKey] = useState("");
  const [zoom, setZoom] = useState(1);
  const [showAllDetails, setShowAllDetails] = useState(true);

  const nodes = Array.isArray(network?.nodes) ? network.nodes : [];
  const edges = Array.isArray(network?.edges) ? network.edges : [];

  const maximumNodeRecords = useMemo(
    () => Math.max(1, ...nodes.map((node) => Number(node.total_records) || 1)),
    [nodes],
  );

  const maximumEdgeRecords = useMemo(
    () => Math.max(1, ...edges.map((edge) => Number(edge.total_records) || 1)),
    [edges],
  );

  const positions = useMemo(
    () => buildForceLayout(nodes, edges),
    [nodes, edges],
  );

  const selectedNode = useMemo(
    () =>
      nodes.find((node) => node.phone_number === selectedNodeNumber) || null,
    [nodes, selectedNodeNumber],
  );

  const selectedEdge = useMemo(
    () =>
      edges.find(
        (edge) => `${edge.source}|${edge.target}` === selectedEdgeKey,
      ) || null,
    [edges, selectedEdgeKey],
  );

  const selectedNodeEdges = useMemo(() => {
    if (!selectedNode) {
      return [];
    }

    return edges
      .filter(
        (edge) =>
          edge.source === selectedNode.phone_number ||
          edge.target === selectedNode.phone_number,
      )
      .sort((first, second) => second.total_records - first.total_records);
  }, [edges, selectedNode]);

  if (nodes.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <Network size={38} className="mx-auto text-slate-300" />
        <h3 className="mt-4 font-bold text-slate-900">
          No communication network found
        </h3>
        <p className="mt-2 text-sm text-slate-500">
          No caller-to-receiver relationship involving this number exists in the
          selected evidence.
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 p-5">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <h2 className="text-lg font-bold text-slate-950">
              Multi-level communication network
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
              Blue links connect the selected number with direct contacts.
              Violet links show communication between associated numbers. A link
              is displayed only when that caller-and-receiver pair exists in the
              selected CDR evidence.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
              {network.node_count} numbers
            </span>
            <span className="rounded-full bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700">
              {network.edge_count} communication links
            </span>
            <span className="rounded-full bg-cyan-50 px-3 py-1.5 text-xs font-semibold text-cyan-700">
              {network.direct_contact_count || 0} direct contacts
            </span>
            <span className="rounded-full bg-fuchsia-50 px-3 py-1.5 text-xs font-semibold text-fuchsia-700">
              {network.peer_link_count || 0} contact-to-contact links
            </span>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 font-semibold text-blue-700">
              <Phone size={14} /> Selected number
            </span>
            <span className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1.5 font-semibold text-sky-700">
              <Users size={14} /> Direct contacts
            </span>
            <span className="inline-flex items-center gap-2 rounded-full bg-violet-50 px-3 py-1.5 font-semibold text-violet-700">
              <Network size={14} /> Contacts of contacts
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setZoom((value) => Math.max(0.65, value - 0.15))}
              className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50"
              title="Zoom out"
            >
              <ZoomOut size={17} />
            </button>
            <span className="min-w-14 text-center text-xs font-semibold text-slate-500">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoom((value) => Math.min(1.65, value + 0.15))}
              className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50"
              title="Zoom in"
            >
              <ZoomIn size={17} />
            </button>
            <button
              type="button"
              onClick={() => {
                setZoom(1);
                setSelectedNodeNumber("");
                setSelectedEdgeKey("");
              }}
              className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50"
              title="Reset view"
            >
              <RotateCcw size={17} />
            </button>
          </div>
        </div>
      </div>

      {Number(network.peer_link_count || 0) === 0 &&
        Number(network.requested_depth) > 1 && (
          <div className="border-b border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-800">
            The selected evidence contains direct links for this number, but no
            communication records were found between the displayed contacts. The
            analyzer does not invent contact-to-contact relationships.
          </div>
        )}

      <div className="overflow-auto bg-gradient-to-br from-slate-50 via-white to-blue-50/50">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="min-h-[720px] min-w-[1050px] w-full"
          role="img"
          aria-label={`Communication network for ${network.root_number}`}
        >
          <defs>
            <pattern
              id="network-grid"
              width="28"
              height="28"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="2" cy="2" r="1" fill="#cbd5e1" opacity="0.45" />
            </pattern>
            <filter
              id="node-shadow"
              x="-40%"
              y="-40%"
              width="180%"
              height="180%"
            >
              <feDropShadow
                dx="0"
                dy="5"
                stdDeviation="5"
                floodColor="#0f172a"
                floodOpacity="0.14"
              />
            </filter>
          </defs>

          <rect width={WIDTH} height={HEIGHT} fill="url(#network-grid)" />

          <g
            transform={`translate(${WIDTH / 2} ${HEIGHT / 2}) scale(${zoom}) translate(${-WIDTH / 2} ${-HEIGHT / 2})`}
          >
            {edges.map((edge) => {
              const source = positions[edge.source];
              const target = positions[edge.target];

              if (!source || !target) {
                return null;
              }

              const edgeKey = `${edge.source}|${edge.target}`;
              const curve = getCurvePath(source, target, edge);
              const records = Number(edge.total_records) || 1;
              const width = 1.5 + (records / maximumEdgeRecords) * 7;
              const selected = selectedEdgeKey === edgeKey;
              const touchesSelectedNode =
                selectedNodeNumber &&
                (edge.source === selectedNodeNumber ||
                  edge.target === selectedNodeNumber);
              const dimmed =
                selectedNodeNumber && !touchesSelectedNode && !selected;
              const peer = edge.relationship_type === "peer_link";

              return (
                <g
                  key={edgeKey}
                  role="button"
                  tabIndex="0"
                  onClick={() => {
                    setSelectedEdgeKey(edgeKey);
                    setSelectedNodeNumber("");
                  }}
                  className="cursor-pointer"
                  opacity={dimmed ? 0.16 : 1}
                >
                  <path
                    d={curve.path}
                    fill="none"
                    stroke={selected ? "#f97316" : peer ? "#8b5cf6" : "#60a5fa"}
                    strokeWidth={selected ? width + 3 : width}
                    strokeLinecap="round"
                    opacity={peer ? 0.72 : 0.82}
                  />

                  {(nodes.length <= 45 || selected || touchesSelectedNode) && (
                    <g>
                      <rect
                        x={curve.labelX - 18}
                        y={curve.labelY - 11}
                        width="36"
                        height="22"
                        rx="11"
                        fill="#ffffff"
                        stroke={peer ? "#c4b5fd" : "#bfdbfe"}
                      />
                      <text
                        x={curve.labelX}
                        y={curve.labelY + 4}
                        textAnchor="middle"
                        fill="#334155"
                        fontSize="10"
                        fontWeight="700"
                      >
                        {records}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {nodes.map((node) => {
              const position = positions[node.phone_number];

              if (!position) {
                return null;
              }

              const radius = getNodeRadius(node, maximumNodeRecords);
              const theme = getNodeTheme(node);
              const selected = selectedNodeNumber === node.phone_number;
              const connectedToSelected =
                !selectedNodeNumber ||
                selected ||
                edges.some(
                  (edge) =>
                    (edge.source === selectedNodeNumber &&
                      edge.target === node.phone_number) ||
                    (edge.target === selectedNodeNumber &&
                      edge.source === node.phone_number),
                );

              return (
                <g
                  key={node.phone_number}
                  role="button"
                  tabIndex="0"
                  onClick={() => {
                    setSelectedNodeNumber(node.phone_number);
                    setSelectedEdgeKey("");
                  }}
                  className="cursor-pointer"
                  opacity={connectedToSelected ? 1 : 0.25}
                  filter="url(#node-shadow)"
                >
                  {(selected || node.is_root) && (
                    <circle
                      cx={position.x}
                      cy={position.y}
                      r={radius + (selected ? 10 : 7)}
                      fill={theme.halo}
                      opacity="0.75"
                    />
                  )}
                  <circle
                    cx={position.x}
                    cy={position.y}
                    r={radius}
                    fill={theme.fill}
                    stroke={selected ? "#f97316" : theme.stroke}
                    strokeWidth={selected ? 5 : node.is_root ? 4 : 3}
                  />
                  <text
                    x={position.x}
                    y={position.y - 7}
                    textAnchor="middle"
                    fill={theme.text}
                    fontSize={node.is_root ? 14 : 10.5}
                    fontWeight="800"
                  >
                    {node.is_root ? "Selected number" : node.phone_number}
                  </text>
                  {node.is_root && (
                    <text
                      x={position.x}
                      y={position.y + 13}
                      textAnchor="middle"
                      fill={theme.text}
                      fontSize="13"
                      fontWeight="700"
                    >
                      {node.phone_number}
                    </text>
                  )}
                  <text
                    x={position.x}
                    y={node.is_root ? position.y + 32 : position.y + 12}
                    textAnchor="middle"
                    fill={theme.text}
                    fontSize="9.5"
                  >
                    {node.total_records} records · {node.contact_count || 0}{" "}
                    links
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {(selectedNode || selectedEdge) && (
        <div className="border-t border-slate-200 bg-slate-50 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                {selectedNode
                  ? "Selected number details"
                  : "Selected communication link"}
              </p>
              <h3 className="mt-1 text-lg font-bold text-slate-950">
                {selectedNode
                  ? selectedNode.phone_number
                  : `${selectedEdge.source} ↔ ${selectedEdge.target}`}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => {
                setSelectedNodeNumber("");
                setSelectedEdgeKey("");
              }}
              className="text-sm font-semibold text-slate-500 hover:text-slate-800"
            >
              Close
            </button>
          </div>

          {selectedNode && (
            <>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <DetailValue label="Network level" value={selectedNode.depth} />
                <DetailValue
                  label="Total records"
                  value={selectedNode.total_records}
                />
                <DetailValue
                  label="Outgoing records"
                  value={selectedNode.outgoing_records || 0}
                />
                <DetailValue
                  label="Incoming records"
                  value={selectedNode.incoming_records || 0}
                />
                <DetailValue
                  label="Call records"
                  value={selectedNode.call_records || 0}
                />
                <DetailValue
                  label="SMS records"
                  value={selectedNode.sms_records || 0}
                />
                <DetailValue
                  label="Connected numbers"
                  value={selectedNode.contact_count || 0}
                />
                <DetailValue
                  label="Total duration"
                  value={formatVisualizationDuration(
                    selectedNode.total_duration_seconds,
                  )}
                />
              </div>

              {selectedNodeEdges.length > 0 && (
                <div className="mt-4 rounded-xl bg-white ring-1 ring-slate-200">
                  <button
                    type="button"
                    onClick={() => setShowAllDetails((value) => !value)}
                    className="flex w-full items-center justify-between px-4 py-3 text-left"
                  >
                    <span className="font-bold text-slate-900">
                      Contacts linked with {selectedNode.phone_number}
                    </span>
                    {showAllDetails ? (
                      <ChevronUp size={18} />
                    ) : (
                      <ChevronDown size={18} />
                    )}
                  </button>

                  {showAllDetails && (
                    <div className="border-t border-slate-200 p-4">
                      <div className="flex flex-wrap gap-2">
                        {selectedNodeEdges.map((edge) => {
                          const otherNumber =
                            edge.source === selectedNode.phone_number
                              ? edge.target
                              : edge.source;

                          return (
                            <button
                              key={`${edge.source}-${edge.target}`}
                              type="button"
                              onClick={() => {
                                setSelectedEdgeKey(
                                  `${edge.source}|${edge.target}`,
                                );
                                setSelectedNodeNumber("");
                              }}
                              className="rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100"
                            >
                              {otherNumber} · {edge.total_records} records
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {selectedEdge && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <DetailValue
                label="Total records"
                value={selectedEdge.total_records}
              />
              <DetailValue label="Calls" value={selectedEdge.total_calls} />
              <DetailValue label="SMS" value={selectedEdge.total_sms} />
              <DetailValue
                label="Total duration"
                value={formatVisualizationDuration(
                  selectedEdge.total_duration_seconds,
                )}
              />
              <DetailValue
                label={`${selectedEdge.source} → ${selectedEdge.target}`}
                value={selectedEdge.source_to_target_records || 0}
              />
              <DetailValue
                label={`${selectedEdge.target} → ${selectedEdge.source}`}
                value={selectedEdge.target_to_source_records || 0}
              />
              <DetailValue
                label="First contact"
                value={
                  selectedEdge.first_contact
                    ? new Date(selectedEdge.first_contact).toLocaleString(
                        "en-IN",
                      )
                    : "—"
                }
              />
              <DetailValue
                label="Last contact"
                value={
                  selectedEdge.last_contact
                    ? new Date(selectedEdge.last_contact).toLocaleString(
                        "en-IN",
                      )
                    : "—"
                }
              />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
