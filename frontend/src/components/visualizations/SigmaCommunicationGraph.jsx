import {
  Download,
  Focus,
  Minus,
  Plus,
  RotateCcw,
  Search,
  Share2,
} from "lucide-react";

import { useEffect, useMemo, useRef, useState } from "react";

import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import Sigma from "sigma";

const SELECTED_COLOR = "#2563EB";
const MUTED_NODE_COLOR = "#D8E1EE";
const MUTED_EDGE_COLOR = "#E2E8F0";
const DISCONNECTED_COLOR = "#CBD5E1";
const REGULAR_NODE_SIZE = 8.5;
const SELECTED_NODE_SIZE = 19;
const EDGE_HOVER_DELAY_MS = 500;
const EDGE_HOVER_TOLERANCE_PX = 12;
const EDGE_HOVER_STICKY_TOLERANCE_PX = 18;

const DISTANCE_STYLES = [
  {
    key: "selected",
    minimum: 0,
    maximum: 0,
    color: SELECTED_COLOR,
    label: "Analysed number",
    shortLabel: "Selected",
  },
  {
    key: "distance-1",
    minimum: 1,
    maximum: 1,
    color: "#F59E0B",
    label: "Directly connected — 1 communication hop",
    shortLabel: "1 hop",
  },
  {
    key: "distance-2",
    minimum: 2,
    maximum: 2,
    color: "#22C55E",
    label: "2 communication hops from the analysed number",
    shortLabel: "2 hops",
  },
  {
    key: "distance-3",
    minimum: 3,
    maximum: 3,
    color: "#8B5CF6",
    label: "3 communication hops from the analysed number",
    shortLabel: "3 hops",
  },
  {
    key: "distance-4",
    minimum: 4,
    maximum: 4,
    color: "#EC4899",
    label: "4 communication hops from the analysed number",
    shortLabel: "4 hops",
  },
  {
    key: "distance-5",
    minimum: 5,
    maximum: 5,
    color: "#06B6D4",
    label: "5 communication hops from the analysed number",
    shortLabel: "5 hops",
  },
  {
    key: "distance-6-plus",
    minimum: 6,
    maximum: Number.POSITIVE_INFINITY,
    color: "#64748B",
    label: "6 or more communication hops from the analysed number",
    shortLabel: "6+ hops",
  },
];

function formatDuration(seconds) {
  const value = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const remainingSeconds = value % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${remainingSeconds}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN");
}

function relationType(edge) {
  const calls = Number(edge.total_calls) || 0;
  const sms = Number(edge.total_sms) || 0;

  if (calls > 0 && sms > 0) {
    return "both";
  }

  if (sms > 0) {
    return "sms";
  }

  return "calls";
}

function relationColor(type) {
  if (type === "sms") {
    return "#A855F7";
  }

  if (type === "both") {
    return "#64748B";
  }

  return "#3B82F6";
}

function edgeMatchesLinkFilter(edge, linkFilter) {
  const edgeType = edge.relation_type || relationType(edge);

  if (linkFilter === "calls") {
    return Number(edge.total_calls) > 0;
  }

  if (linkFilter === "sms") {
    return Number(edge.total_sms) > 0;
  }

  if (linkFilter === "both") {
    return edgeType === "both";
  }

  return true;
}

function distanceFromPointToSegment(point, start, end) {
  const segmentX = end.x - start.x;
  const segmentY = end.y - start.y;
  const segmentLengthSquared = segmentX * segmentX + segmentY * segmentY;

  if (segmentLengthSquared === 0) {
    return Math.hypot(point.x - start.x, point.y - start.y);
  }

  const projection = Math.max(
    0,
    Math.min(
      1,
      ((point.x - start.x) * segmentX + (point.y - start.y) * segmentY) /
        segmentLengthSquared,
    ),
  );

  const nearestX = start.x + projection * segmentX;
  const nearestY = start.y + projection * segmentY;

  return Math.hypot(point.x - nearestX, point.y - nearestY);
}

function deterministicFraction(value) {
  const textValue = String(value || "");
  let hash = 2166136261;

  for (let index = 0; index < textValue.length; index += 1) {
    hash ^= textValue.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return (hash >>> 0) / 4294967295;
}

function getDistanceStyle(distance) {
  if (
    distance === null ||
    distance === undefined ||
    !Number.isFinite(distance)
  ) {
    return {
      key: "disconnected",
      color: DISCONNECTED_COLOR,
      label: "Outside the analysed number's connected component",
      shortLabel: "Not connected",
    };
  }

  return (
    DISTANCE_STYLES.find(
      (style) => distance >= style.minimum && distance <= style.maximum,
    ) || DISTANCE_STYLES[DISTANCE_STYLES.length - 1]
  );
}

function calculateShortestDistances(graph, selectedNumber) {
  const distances = new Map();

  if (!selectedNumber || !graph.hasNode(selectedNumber)) {
    return distances;
  }

  const queue = [selectedNumber];
  let queueIndex = 0;
  distances.set(selectedNumber, 0);

  while (queueIndex < queue.length) {
    const currentNode = queue[queueIndex];
    queueIndex += 1;
    const currentDistance = distances.get(currentNode) || 0;

    graph.forEachNeighbor(currentNode, (neighbour) => {
      if (distances.has(neighbour)) {
        return;
      }

      distances.set(neighbour, currentDistance + 1);
      queue.push(neighbour);
    });
  }

  return distances;
}

function adaptiveRingSpacing(nodeCount) {
  if (nodeCount <= 15) {
    return 8.5;
  }

  if (nodeCount <= 30) {
    return 11.5;
  }

  if (nodeCount <= 60) {
    return 15;
  }

  if (nodeCount <= 100) {
    return 19;
  }

  return Math.min(34, 22 + nodeCount / 22);
}

function placeNodesByShortestDistance(graph, selectedNumber, distances) {
  if (!selectedNumber || !graph.hasNode(selectedNumber)) {
    return {
      maxDistance: 0,
      ringSpacing: adaptiveRingSpacing(graph.order),
    };
  }

  const ringSpacing = adaptiveRingSpacing(graph.order);
  const groups = new Map();
  const disconnectedNodes = [];

  graph.forEachNode((node) => {
    const distance = distances.get(node);

    if (distance === undefined) {
      disconnectedNodes.push(node);
      return;
    }

    if (!groups.has(distance)) {
      groups.set(distance, []);
    }

    groups.get(distance).push(node);
  });

  const maxDistance = Math.max(
    0,
    ...[...groups.keys()].filter((distance) => Number.isFinite(distance)),
  );

  graph.mergeNodeAttributes(selectedNumber, {
    x: 0,
    y: 0,
  });

  [...groups.entries()]
    .filter(([distance]) => distance > 0)
    .sort(([distanceA], [distanceB]) => distanceA - distanceB)
    .forEach(([distance, members]) => {
      const sortedMembers = [...members].sort((nodeA, nodeB) => {
        const angleA = Math.atan2(
          Number(graph.getNodeAttribute(nodeA, "y")) || 0,
          Number(graph.getNodeAttribute(nodeA, "x")) || 0,
        );
        const angleB = Math.atan2(
          Number(graph.getNodeAttribute(nodeB, "y")) || 0,
          Number(graph.getNodeAttribute(nodeB, "x")) || 0,
        );

        return angleA - angleB;
      });

      const minimumArcSpacing =
        graph.order > 80 ? 4.1 : graph.order > 40 ? 3.6 : 3.1;
      const radiusFromNodeCount =
        (sortedMembers.length * minimumArcSpacing) / (Math.PI * 2);
      const baseRadius = Math.max(
        distance * ringSpacing,
        radiusFromNodeCount + distance * 1.8,
      );
      const angleOffset =
        deterministicFraction(`ring-${distance}`) * Math.PI * 2;

      sortedMembers.forEach((node, index) => {
        const angle =
          angleOffset +
          (index / Math.max(sortedMembers.length, 1)) * Math.PI * 2;
        const smallRadialVariation =
          (deterministicFraction(node) - 0.5) *
          Math.min(2.6, ringSpacing * 0.16);
        const radius = baseRadius + smallRadialVariation;

        graph.mergeNodeAttributes(node, {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
        });
      });
    });

  if (disconnectedNodes.length > 0) {
    const disconnectedRingIndex = Math.max(1, maxDistance + 1);
    const minimumArcSpacing = graph.order > 80 ? 4.3 : 3.7;
    const disconnectedRadius = Math.max(
      disconnectedRingIndex * ringSpacing + ringSpacing,
      (disconnectedNodes.length * minimumArcSpacing) / (Math.PI * 2) +
        disconnectedRingIndex * 2,
    );
    const angleOffset = Math.PI / 7;

    disconnectedNodes
      .sort((nodeA, nodeB) => String(nodeA).localeCompare(String(nodeB)))
      .forEach((node, index) => {
        const angle =
          angleOffset +
          (index / Math.max(disconnectedNodes.length, 1)) * Math.PI * 2;
        const variation =
          (deterministicFraction(node) - 0.5) * ringSpacing * 0.25;

        graph.mergeNodeAttributes(node, {
          x: Math.cos(angle) * (disconnectedRadius + variation),
          y: Math.sin(angle) * (disconnectedRadius + variation),
        });
      });
  }

  return {
    maxDistance,
    ringSpacing,
  };
}

function createGraph(network) {
  const graph = new Graph({
    type: "undirected",
    multi: false,
    allowSelfLoops: false,
  });

  const nodes = Array.isArray(network?.nodes) ? network.nodes : [];
  const edges = Array.isArray(network?.edges) ? network.edges : [];
  const selectedNumber = String(network?.selected_number || "");

  nodes.forEach((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
    const initialRadius = 8 + Math.sqrt(Math.max(nodes.length, 1)) * 0.8;

    graph.addNode(node.phone_number, {
      ...node,
      label: node.phone_number,
      x: Math.cos(angle) * initialRadius,
      y: Math.sin(angle) * initialRadius,
      size: 7,
      color: "#93C5FD",
    });
  });

  edges.forEach((edge, index) => {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) {
      return;
    }

    const type = relationType(edge);

    graph.addUndirectedEdgeWithKey(
      `relationship-${index}`,
      edge.source,
      edge.target,
      {
        ...edge,
        relation_type: type,
        weight: Math.max(1, Number(edge.total_records) || 1),
        size: 1 + Math.log2(1 + (Number(edge.total_records) || 1)) * 0.65,
        color: relationColor(type),
      },
    );
  });

  if (graph.order > 1 && graph.size > 0) {
    const inferredSettings = forceAtlas2.inferSettings(graph);
    const denseGraph = graph.order > 40;
    const veryDenseGraph = graph.order > 90;

    forceAtlas2.assign(graph, {
      iterations: Math.min(850, Math.max(220, graph.order * 13)),
      getEdgeWeight: "weight",
      settings: {
        ...inferredSettings,
        adjustSizes: true,
        barnesHutOptimize: graph.order > 80,
        edgeWeightInfluence: denseGraph ? 0.22 : 0.38,
        gravity: veryDenseGraph ? 0.16 : denseGraph ? 0.24 : 0.48,
        linLogMode: true,
        scalingRatio: veryDenseGraph
          ? Math.min(90, 28 + graph.order * 0.42)
          : denseGraph
            ? Math.min(55, 18 + graph.order * 0.32)
            : 13,
        slowDown: veryDenseGraph ? 15 : denseGraph ? 12 : 9,
        strongGravityMode: false,
      },
    });
  }

  if (selectedNumber && graph.hasNode(selectedNumber)) {
    const selectedX = Number(graph.getNodeAttribute(selectedNumber, "x")) || 0;
    const selectedY = Number(graph.getNodeAttribute(selectedNumber, "y")) || 0;

    graph.forEachNode((node) => {
      graph.updateNodeAttribute(
        node,
        "x",
        (value) => Number(value) - selectedX,
      );
      graph.updateNodeAttribute(
        node,
        "y",
        (value) => Number(value) - selectedY,
      );
    });
  }

  const shortestDistances = calculateShortestDistances(graph, selectedNumber);
  const placement = placeNodesByShortestDistance(
    graph,
    selectedNumber,
    shortestDistances,
  );

  graph.forEachNode((node) => {
    const isSelected = node === selectedNumber;
    const rawDistance = shortestDistances.get(node);
    const distance = rawDistance === undefined ? null : Number(rawDistance);
    const distanceStyle = getDistanceStyle(distance);

    graph.mergeNodeAttributes(node, {
      size: isSelected ? SELECTED_NODE_SIZE : REGULAR_NODE_SIZE,
      baseSize: isSelected ? SELECTED_NODE_SIZE : REGULAR_NODE_SIZE,
      color: distanceStyle.color,
      baseColor: distanceStyle.color,
      distance_from_selected: distance,
      distance_label: distanceStyle.label,
      is_analysed_number: isSelected,
    });
  });

  const distanceCounts = new Map();
  let disconnectedCount = 0;

  graph.forEachNode((node, attributes) => {
    const distance = attributes.distance_from_selected;

    if (distance === null || distance === undefined) {
      disconnectedCount += 1;
      return;
    }

    const numericDistance = Number(distance);
    const bucket = numericDistance >= 6 ? 6 : numericDistance;
    distanceCounts.set(bucket, (distanceCounts.get(bucket) || 0) + 1);
  });

  const distanceLegend = DISTANCE_STYLES.map((style) => {
    const bucket = style.minimum >= 6 ? 6 : style.minimum;

    return {
      ...style,
      count: distanceCounts.get(bucket) || 0,
    };
  }).filter((style) => style.count > 0);

  if (disconnectedCount > 0) {
    distanceLegend.push({
      key: "disconnected",
      color: DISCONNECTED_COLOR,
      label: "Outside the analysed number's connected component",
      shortLabel: "Not connected",
      count: disconnectedCount,
    });
  }

  return {
    graph,
    distanceLegend,
    maxDistance: placement.maxDistance,
    ringSpacing: placement.ringSpacing,
  };
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-semibold text-slate-900">{value}</span>
    </div>
  );
}

function MetricBadge({ label, value }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700">
      <span>{label}</span>
      <strong>{value}</strong>
    </span>
  );
}

export default function SigmaCommunicationGraph({ network }) {
  const containerRef = useRef(null);
  const sigmaRef = useRef(null);
  const graphRef = useRef(null);
  const edgeHoverTimerRef = useRef(null);
  const edgeHoverFrameRef = useRef(null);
  const pendingHoveredEdgeRef = useRef(null);
  const pendingEdgeTooltipRef = useRef(null);
  const visibleHoveredEdgeRef = useRef(null);
  const latestPointerPositionRef = useRef(null);
  const linkFilterRef = useRef("all");

  const [selectedNode, setSelectedNode] = useState(
    String(network?.selected_number || ""),
  );
  const [focusedNode, setFocusedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [linkFilter, setLinkFilter] = useState("all");
  const [searchValue, setSearchValue] = useState("");

  const graphModel = useMemo(() => createGraph(network), [network]);

  useEffect(() => {
    linkFilterRef.current = linkFilter;
  }, [linkFilter]);

  const nodesByNumber = useMemo(() => {
    return Object.fromEntries(
      (network?.nodes || []).map((node) => [node.phone_number, node]),
    );
  }, [network]);

  const edges = useMemo(
    () => (Array.isArray(network?.edges) ? network.edges : []),
    [network],
  );

  useEffect(() => {
    setSelectedNode(String(network?.selected_number || ""));
    setFocusedNode(null);
    setHoveredNode(null);
    setSelectedEdge(null);
    setHoveredEdge(null);

    if (edgeHoverTimerRef.current) {
      window.clearTimeout(edgeHoverTimerRef.current);
      edgeHoverTimerRef.current = null;
    }

    pendingHoveredEdgeRef.current = null;
    pendingEdgeTooltipRef.current = null;
    visibleHoveredEdgeRef.current = null;
    latestPointerPositionRef.current = null;
    linkFilterRef.current = "all";
    setLinkFilter("all");
    setSearchValue("");
  }, [network]);

  useEffect(() => {
    if (!containerRef.current) {
      return undefined;
    }

    const sigma = new Sigma(graphModel.graph, containerRef.current, {
      allowInvalidContainer: true,
      defaultNodeColor: "#93C5FD",
      defaultEdgeColor: "#CBD5E1",
      edgeLabelColor: { color: "#475569" },
      enableEdgeEvents: true,
      hideEdgesOnMove: false,
      hideLabelsOnMove: false,
      labelColor: { color: "#0F172A" },
      labelDensity:
        graphModel.graph.order > 80
          ? 0.035
          : graphModel.graph.order > 40
            ? 0.055
            : 0.08,
      labelFont: "Inter, ui-sans-serif, system-ui, sans-serif",
      labelGridCellSize: graphModel.graph.order > 60 ? 145 : 120,
      labelRenderedSizeThreshold: graphModel.graph.order > 60 ? 11 : 9,
      labelSize: 12,
      minCameraRatio: 0.04,
      maxCameraRatio: 12,
      renderEdgeLabels: false,
      stagePadding: 40,
      zIndex: true,
    });

    sigmaRef.current = sigma;
    graphRef.current = graphModel.graph;

    sigma.on("enterNode", ({ node }) => {
      setHoveredNode(node);
    });

    sigma.on("leaveNode", () => {
      setHoveredNode(null);
    });

    sigma.on("clickNode", ({ node }) => {
      setSelectedNode(node);
      setFocusedNode(node);
      setSelectedEdge(null);
    });

    const hideEdgeTooltip = () => {
      if (edgeHoverTimerRef.current) {
        window.clearTimeout(edgeHoverTimerRef.current);
        edgeHoverTimerRef.current = null;
      }

      pendingHoveredEdgeRef.current = null;
      pendingEdgeTooltipRef.current = null;
      visibleHoveredEdgeRef.current = null;
      setHoveredEdge(null);
    };

    const tooltipPosition = (x, y) => {
      const container = containerRef.current;
      const width = container?.clientWidth || 0;
      const height = container?.clientHeight || 0;
      const tooltipWidth = 310;
      const tooltipHeight = 210;

      return {
        x: Math.max(12, Math.min(x + 16, width - tooltipWidth - 12)),
        y: Math.max(12, Math.min(y + 16, height - tooltipHeight - 12)),
      };
    };

    const distanceToEdge = (edge, point) => {
      if (!graphModel.graph.hasEdge(edge)) {
        return Number.POSITIVE_INFINITY;
      }

      const attributes = graphModel.graph.getEdgeAttributes(edge);

      if (!edgeMatchesLinkFilter(attributes, linkFilterRef.current)) {
        return Number.POSITIVE_INFINITY;
      }

      const [source, target] = graphModel.graph.extremities(edge);
      const sourceAttributes = graphModel.graph.getNodeAttributes(source);
      const targetAttributes = graphModel.graph.getNodeAttributes(target);

      const sourcePosition = sigma.graphToViewport({
        x: Number(sourceAttributes.x) || 0,
        y: Number(sourceAttributes.y) || 0,
      });

      const targetPosition = sigma.graphToViewport({
        x: Number(targetAttributes.x) || 0,
        y: Number(targetAttributes.y) || 0,
      });

      return distanceFromPointToSegment(point, sourcePosition, targetPosition);
    };

    const findNearestEdge = (point) => {
      const preferredEdge =
        visibleHoveredEdgeRef.current || pendingHoveredEdgeRef.current;

      if (
        preferredEdge &&
        distanceToEdge(preferredEdge, point) <= EDGE_HOVER_STICKY_TOLERANCE_PX
      ) {
        return preferredEdge;
      }

      let nearestEdge = null;
      let nearestDistance = EDGE_HOVER_TOLERANCE_PX;

      graphModel.graph.forEachEdge((edge, attributes) => {
        if (!edgeMatchesLinkFilter(attributes, linkFilterRef.current)) {
          return;
        }

        const distance = distanceToEdge(edge, point);

        if (distance <= nearestDistance) {
          nearestDistance = distance;
          nearestEdge = edge;
        }
      });

      return nearestEdge;
    };

    const processPointerPosition = () => {
      edgeHoverFrameRef.current = null;

      const pointer = latestPointerPositionRef.current;

      if (!pointer) {
        hideEdgeTooltip();
        return;
      }

      const nearestEdge = findNearestEdge(pointer);

      if (!nearestEdge) {
        hideEdgeTooltip();
        return;
      }

      const position = tooltipPosition(pointer.x, pointer.y);
      pendingEdgeTooltipRef.current = {
        edge: nearestEdge,
        ...position,
      };

      if (visibleHoveredEdgeRef.current === nearestEdge) {
        setHoveredEdge({
          edge: nearestEdge,
          ...position,
        });
        return;
      }

      if (pendingHoveredEdgeRef.current === nearestEdge) {
        return;
      }

      if (edgeHoverTimerRef.current) {
        window.clearTimeout(edgeHoverTimerRef.current);
      }

      setHoveredEdge(null);
      visibleHoveredEdgeRef.current = null;
      pendingHoveredEdgeRef.current = nearestEdge;

      edgeHoverTimerRef.current = window.setTimeout(() => {
        if (pendingHoveredEdgeRef.current !== nearestEdge) {
          return;
        }

        const latestTooltip = pendingEdgeTooltipRef.current;

        if (!latestTooltip || latestTooltip.edge !== nearestEdge) {
          return;
        }

        visibleHoveredEdgeRef.current = nearestEdge;
        setHoveredEdge(latestTooltip);
        edgeHoverTimerRef.current = null;
      }, EDGE_HOVER_DELAY_MS);
    };

    const handleGraphPointerMove = (event) => {
      const container = containerRef.current;

      if (!container) {
        return;
      }

      const bounds = container.getBoundingClientRect();

      latestPointerPositionRef.current = {
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      };

      if (edgeHoverFrameRef.current) {
        return;
      }

      edgeHoverFrameRef.current = window.requestAnimationFrame(
        processPointerPosition,
      );
    };

    const handleGraphPointerLeave = () => {
      latestPointerPositionRef.current = null;

      if (edgeHoverFrameRef.current) {
        window.cancelAnimationFrame(edgeHoverFrameRef.current);
        edgeHoverFrameRef.current = null;
      }

      hideEdgeTooltip();
    };

    const graphContainer = containerRef.current;

    graphContainer.addEventListener("pointermove", handleGraphPointerMove, {
      passive: true,
    });
    graphContainer.addEventListener("pointerleave", handleGraphPointerLeave);

    sigma.on("clickEdge", ({ edge }) => {
      hideEdgeTooltip();
      setSelectedEdge(edge);
      setHoveredEdge(null);
      setFocusedNode(null);
    });

    sigma.on("clickStage", () => {
      hideEdgeTooltip();
      setFocusedNode(null);
      setSelectedEdge(null);
      setHoveredEdge(null);
    });

    sigma.getCamera().animatedReset({ duration: 300 });

    return () => {
      graphContainer.removeEventListener("pointermove", handleGraphPointerMove);
      graphContainer.removeEventListener(
        "pointerleave",
        handleGraphPointerLeave,
      );

      if (edgeHoverTimerRef.current) {
        window.clearTimeout(edgeHoverTimerRef.current);
        edgeHoverTimerRef.current = null;
      }

      if (edgeHoverFrameRef.current) {
        window.cancelAnimationFrame(edgeHoverFrameRef.current);
        edgeHoverFrameRef.current = null;
      }

      pendingHoveredEdgeRef.current = null;
      pendingEdgeTooltipRef.current = null;
      visibleHoveredEdgeRef.current = null;
      latestPointerPositionRef.current = null;
      sigma.kill();
      sigmaRef.current = null;
      graphRef.current = null;
    };
  }, [graphModel]);

  useEffect(() => {
    const sigma = sigmaRef.current;
    const graph = graphRef.current;

    if (!sigma || !graph) {
      return;
    }

    const focus = hoveredNode || focusedNode;
    const neighbours = new Set();
    const hoveredEdgeKey = hoveredEdge?.edge || null;
    const hoveredEdgeNodes = new Set();

    if (focus && graph.hasNode(focus)) {
      graph.forEachNeighbor(focus, (neighbour) => neighbours.add(neighbour));
    }

    if (hoveredEdgeKey && graph.hasEdge(hoveredEdgeKey)) {
      const [source, target] = graph.extremities(hoveredEdgeKey);
      hoveredEdgeNodes.add(source);
      hoveredEdgeNodes.add(target);
    }

    sigma.setSetting("nodeReducer", (node, data) => {
      const result = { ...data };
      const isFocus = focus === node;
      const isNeighbour = neighbours.has(node);
      const isDetailSelection = node === selectedNode;
      const isAnalysedNumber = Boolean(data.is_analysed_number);
      const isHoveredEdgeEndpoint = hoveredEdgeNodes.has(node);

      if (hoveredEdgeKey && !isHoveredEdgeEndpoint) {
        result.color = MUTED_NODE_COLOR;
        result.label = "";
        result.zIndex = 0;
      } else if (focus && !isFocus && !isNeighbour) {
        result.color = MUTED_NODE_COLOR;
        result.label = "";
        result.zIndex = 0;
      } else {
        result.color = data.baseColor || data.color;
        result.zIndex =
          isFocus || isAnalysedNumber || isHoveredEdgeEndpoint
            ? 5
            : isDetailSelection
              ? 4
              : isNeighbour
                ? 3
                : 1;
      }

      result.size = isAnalysedNumber ? SELECTED_NODE_SIZE : REGULAR_NODE_SIZE;

      if (
        isFocus ||
        isAnalysedNumber ||
        isDetailSelection ||
        isHoveredEdgeEndpoint
      ) {
        result.forceLabel = true;
        result.highlighted = true;
      }

      return result;
    });

    sigma.setSetting("edgeReducer", (edge, data) => {
      const result = { ...data };
      const edgeType = data.relation_type || relationType(data);

      if (
        linkFilter !== "all" &&
        !(
          (linkFilter === "calls" && Number(data.total_calls) > 0) ||
          (linkFilter === "sms" && Number(data.total_sms) > 0) ||
          (linkFilter === "both" && edgeType === "both")
        )
      ) {
        result.hidden = true;
        return result;
      }

      if (hoveredEdgeKey) {
        if (edge !== hoveredEdgeKey) {
          result.color = MUTED_EDGE_COLOR;
          result.size = 0.45;
          result.zIndex = 0;
        } else {
          result.color = relationColor(edgeType);
          result.size = Number(data.size || 1) + 2.2;
          result.zIndex = 6;
        }
      } else if (focus) {
        const [source, target] = graph.extremities(edge);
        const touchesFocus = source === focus || target === focus;

        if (!touchesFocus) {
          result.color = MUTED_EDGE_COLOR;
          result.size = 0.5;
          result.zIndex = 0;
        } else {
          result.color = relationColor(edgeType);
          result.size = Number(data.size || 1) + 1.2;
          result.zIndex = 3;
        }
      }

      if (edge === selectedEdge) {
        result.color = "#0F172A";
        result.size = Number(data.size || 1) + 2;
        result.zIndex = 7;
      }

      return result;
    });

    sigma.refresh();
  }, [
    focusedNode,
    hoveredEdge,
    hoveredNode,
    linkFilter,
    selectedEdge,
    selectedNode,
  ]);

  const selectedNodeData = nodesByNumber[selectedNode] || null;

  const selectedNodeEdges = useMemo(() => {
    if (!selectedNode) {
      return [];
    }

    return edges
      .filter(
        (edge) => edge.source === selectedNode || edge.target === selectedNode,
      )
      .sort((a, b) => Number(b.total_records) - Number(a.total_records));
  }, [edges, selectedNode]);

  const selectedEdgeData = useMemo(() => {
    const graph = graphRef.current;

    if (!selectedEdge || !graph || !graph.hasEdge(selectedEdge)) {
      return null;
    }

    const [source, target] = graph.extremities(selectedEdge);

    return {
      source,
      target,
      ...graph.getEdgeAttributes(selectedEdge),
    };
  }, [selectedEdge]);

  const hoveredEdgeData = useMemo(() => {
    const graph = graphModel.graph;
    const edgeKey = hoveredEdge?.edge;

    if (!edgeKey || !graph.hasEdge(edgeKey)) {
      return null;
    }

    const [source, target] = graph.extremities(edgeKey);

    return {
      source,
      target,
      ...graph.getEdgeAttributes(edgeKey),
    };
  }, [graphModel, hoveredEdge]);

  const linkDistribution = useMemo(() => {
    return edges.reduce(
      (accumulator, edge) => {
        const type = relationType(edge);
        accumulator[type] += Number(edge.total_records) || 0;
        accumulator.total += Number(edge.total_records) || 0;
        return accumulator;
      },
      { calls: 0, sms: 0, both: 0, total: 0 },
    );
  }, [edges]);

  function zoomIn() {
    sigmaRef.current?.getCamera().animatedZoom({ duration: 250 });
  }

  function zoomOut() {
    sigmaRef.current?.getCamera().animatedUnzoom({ duration: 250 });
  }

  function resetView() {
    setFocusedNode(null);
    setSelectedEdge(null);
    setHoveredEdge(null);
    setSelectedNode(String(network?.selected_number || ""));
    sigmaRef.current?.getCamera().animatedReset({ duration: 350 });
  }

  function focusSearchedNumber(event) {
    event.preventDefault();
    const number = searchValue.trim();
    const sigma = sigmaRef.current;
    const graph = graphRef.current;

    if (!number || !sigma || !graph || !graph.hasNode(number)) {
      return;
    }

    setSelectedNode(number);
    setFocusedNode(number);
    setSelectedEdge(null);

    const position = sigma.getNodeDisplayData(number);

    if (position) {
      sigma.getCamera().animate(
        {
          x: position.x,
          y: position.y,
          ratio: 0.28,
        },
        { duration: 450 },
      );
    }
  }

  function exportPng() {
    const sigma = sigmaRef.current;

    if (!sigma) {
      return;
    }

    const canvases = sigma.getCanvases();
    const firstCanvas = Object.values(canvases)[0];

    if (!firstCanvas) {
      return;
    }

    const output = document.createElement("canvas");
    output.width = firstCanvas.width;
    output.height = firstCanvas.height;

    const context = output.getContext("2d");

    if (!context) {
      return;
    }

    context.fillStyle = "#F8FBFF";
    context.fillRect(0, 0, output.width, output.height);

    Object.values(canvases).forEach((canvas) => {
      if (canvas && canvas.width && canvas.height) {
        context.drawImage(canvas, 0, 0);
      }
    });

    const link = document.createElement("a");
    link.download = `communication-network-${network?.evidence_id || "evidence"}.png`;
    link.href = output.toDataURL("image/png");
    link.click();
  }

  if (!network || Number(network.node_count) === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
        <Share2 size={40} className="mx-auto text-slate-300" />
        <h3 className="mt-4 font-bold text-slate-900">
          No communication graph is available
        </h3>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
          The selected evidence did not contain a valid caller-and-receiver
          pair.
        </p>
      </div>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 px-5 py-4">
        <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
          <div>
            <div className="flex items-center gap-2">
              <Share2 size={21} className="text-blue-600" />
              <h2 className="text-lg font-bold text-slate-950">
                Full-Evidence Communication Graph
              </h2>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Every node and relationship comes from the complete selected CDR
              evidence. Node colours represent the shortest communication
              distance from the analysed number. When several paths exist, the
              smallest distance is always used. Every non-selected number uses
              the same node size; only the analysed number is larger.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <MetricBadge label="Numbers" value={network.node_count} />
            <MetricBadge label="Relationships" value={network.edge_count} />
            <MetricBadge
              label="Maximum distance"
              value={`${graphModel.maxDistance} hop${
                graphModel.maxDistance === 1 ? "" : "s"
              }`}
            />
            <MetricBadge
              label="Components"
              value={network.connected_component_count}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <form
            onSubmit={focusSearchedNumber}
            className="flex min-w-0 flex-1 items-center gap-2"
          >
            <div className="relative min-w-0 flex-1 lg:max-w-md">
              <Search
                size={17}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={searchValue}
                onChange={(event) => setSearchValue(event.target.value)}
                placeholder="Find a number in this graph"
                className="min-h-11 w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </div>
            <button
              type="submit"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white transition hover:bg-blue-700"
            >
              <Focus size={17} />
              Focus
            </button>
          </form>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={linkFilter}
              onChange={(event) => setLinkFilter(event.target.value)}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            >
              <option value="all">All communication</option>
              <option value="calls">Contains calls</option>
              <option value="sms">Contains SMS</option>
              <option value="both">Calls and SMS</option>
            </select>

            <button
              type="button"
              onClick={resetView}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-blue-700 transition hover:bg-blue-100"
            >
              <RotateCcw size={17} />
              Reset View
            </button>

            <button
              type="button"
              onClick={exportPng}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              <Download size={17} />
              Export PNG
            </button>
          </div>
        </div>
      </header>

      <div className="grid xl:grid-cols-[minmax(0,1fr)_330px]">
        <div className="relative min-h-[720px] overflow-hidden border-b border-slate-200 bg-[radial-gradient(circle_at_top_left,_#eff6ff_0,_#ffffff_40%,_#faf5ff_100%)] xl:border-b-0 xl:border-r">
          <div ref={containerRef} className="absolute inset-0" />

          {hoveredEdge && hoveredEdgeData && (
            <div
              className="pointer-events-none absolute z-30 w-[294px] rounded-2xl border border-blue-100 bg-white/95 p-4 shadow-xl backdrop-blur"
              style={{
                left: `${hoveredEdge.x}px`,
                top: `${hoveredEdge.y}px`,
              }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-wide text-blue-500">
                Communication relationship
              </p>
              <p className="mt-1 break-all text-sm font-bold text-slate-900">
                {hoveredEdgeData.source}
              </p>
              <p className="my-0.5 text-center text-xs font-semibold text-slate-400">
                ↕
              </p>
              <p className="break-all text-sm font-bold text-slate-900">
                {hoveredEdgeData.target}
              </p>

              <div className="mt-3 grid grid-cols-3 gap-2">
                <div className="rounded-xl bg-slate-50 p-2 text-center">
                  <p className="text-[10px] uppercase text-slate-400">
                    Records
                  </p>
                  <p className="mt-1 text-sm font-bold text-slate-900">
                    {hoveredEdgeData.total_records || 0}
                  </p>
                </div>
                <div className="rounded-xl bg-blue-50 p-2 text-center">
                  <p className="text-[10px] uppercase text-blue-400">Calls</p>
                  <p className="mt-1 text-sm font-bold text-blue-700">
                    {hoveredEdgeData.total_calls || 0}
                  </p>
                </div>
                <div className="rounded-xl bg-purple-50 p-2 text-center">
                  <p className="text-[10px] uppercase text-purple-400">SMS</p>
                  <p className="mt-1 text-sm font-bold text-purple-700">
                    {hoveredEdgeData.total_sms || 0}
                  </p>
                </div>
              </div>

              <div className="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-600">
                <p>
                  <span className="font-semibold text-slate-800">First:</span>{" "}
                  {formatDateTime(hoveredEdgeData.first_contact)}
                </p>
                <p className="mt-1">
                  <span className="font-semibold text-slate-800">Last:</span>{" "}
                  {formatDateTime(hoveredEdgeData.last_contact)}
                </p>
              </div>
            </div>
          )}

          <div className="absolute left-4 top-4 z-10 flex flex-col gap-2">
            <button
              type="button"
              onClick={zoomIn}
              aria-label="Zoom in"
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-blue-50 hover:text-blue-700"
            >
              <Plus size={18} />
            </button>
            <button
              type="button"
              onClick={zoomOut}
              aria-label="Zoom out"
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-blue-50 hover:text-blue-700"
            >
              <Minus size={18} />
            </button>
          </div>

          <div className="absolute bottom-4 left-4 right-4 z-10 flex flex-wrap gap-x-4 gap-y-2 rounded-xl border border-blue-100 bg-white/90 p-3 text-xs font-medium text-slate-600 shadow-sm backdrop-blur">
            {graphModel.distanceLegend.map((item) => (
              <span key={item.key} className="inline-flex items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                {item.shortLabel} ({item.count})
              </span>
            ))}
            <span className="inline-flex items-center gap-1.5">
              <span className="h-0.5 w-5 bg-blue-500" />
              Calls
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-0.5 w-5 bg-purple-500" />
              SMS
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-0.5 w-5 bg-slate-500" />
              Calls and SMS
            </span>
            <span className="text-slate-400">
              Keep the pointer near a relationship for 0.5 seconds to see its
              quick summary. Click a number or line for full details.
            </span>
          </div>
        </div>

        <aside className="space-y-4 bg-slate-50/70 p-4">
          {selectedEdgeData ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Selected relationship
              </p>
              <h3 className="mt-2 break-all text-lg font-bold text-slate-950">
                {selectedEdgeData.source}
              </h3>
              <p className="my-1 text-center text-sm font-semibold text-blue-600">
                communicates with
              </p>
              <h3 className="break-all text-lg font-bold text-slate-950">
                {selectedEdgeData.target}
              </h3>

              <div className="mt-4 divide-y divide-slate-100">
                <InfoRow
                  label="Total records"
                  value={selectedEdgeData.total_records}
                />
                <InfoRow label="Calls" value={selectedEdgeData.total_calls} />
                <InfoRow label="SMS" value={selectedEdgeData.total_sms} />
                <InfoRow
                  label={`${selectedEdgeData.source} → ${selectedEdgeData.target}`}
                  value={selectedEdgeData.source_to_target_records}
                />
                <InfoRow
                  label={`${selectedEdgeData.target} → ${selectedEdgeData.source}`}
                  value={selectedEdgeData.target_to_source_records}
                />
                <InfoRow
                  label="Duration"
                  value={formatDuration(
                    selectedEdgeData.total_duration_seconds,
                  )}
                />
                <InfoRow
                  label="First contact"
                  value={formatDateTime(selectedEdgeData.first_contact)}
                />
                <InfoRow
                  label="Last contact"
                  value={formatDateTime(selectedEdgeData.last_contact)}
                />
              </div>
            </div>
          ) : selectedNodeData ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Number details
              </p>
              <h3 className="mt-2 break-all text-2xl font-bold text-blue-700">
                {selectedNodeData.phone_number}
              </h3>

              <div className="mt-4 divide-y divide-slate-100">
                <InfoRow
                  label="Total records"
                  value={selectedNodeData.total_records}
                />
                <InfoRow
                  label="Outgoing"
                  value={selectedNodeData.outgoing_records}
                />
                <InfoRow
                  label="Incoming"
                  value={selectedNodeData.incoming_records}
                />
                <InfoRow label="Calls" value={selectedNodeData.call_records} />
                <InfoRow label="SMS" value={selectedNodeData.sms_records} />
                <InfoRow
                  label="Unique contacts"
                  value={selectedNodeData.contact_count}
                />
                <InfoRow
                  label="Distance from analysed number"
                  value={
                    selectedNodeData.phone_number === network?.selected_number
                      ? "Analysed number"
                      : graphModel.graph.hasNode(selectedNodeData.phone_number)
                        ? graphModel.graph.getNodeAttribute(
                            selectedNodeData.phone_number,
                            "distance_label",
                          )
                        : "Not available"
                  }
                />
                <InfoRow
                  label="Total duration"
                  value={formatDuration(
                    selectedNodeData.total_duration_seconds,
                  )}
                />
                <InfoRow
                  label="First seen"
                  value={formatDateTime(selectedNodeData.first_activity)}
                />
                <InfoRow
                  label="Last seen"
                  value={formatDateTime(selectedNodeData.last_activity)}
                />
                <InfoRow
                  label="Graph role"
                  value={
                    selectedNodeData.is_bridge
                      ? "Bridge between groups"
                      : selectedNodeData.is_hub
                        ? "Highly connected hub"
                        : "Communication participant"
                  }
                />
              </div>
            </div>
          ) : null}

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="font-bold text-slate-950">Top connected numbers</h3>
            <p className="mt-1 text-xs text-slate-500">
              Strongest relationships for the selected number.
            </p>

            <div className="mt-4 space-y-2">
              {selectedNodeEdges.slice(0, 6).map((edge) => {
                const contact =
                  edge.source === selectedNode ? edge.target : edge.source;

                return (
                  <button
                    type="button"
                    key={`${edge.source}-${edge.target}`}
                    onClick={() => {
                      setSelectedNode(contact);
                      setFocusedNode(contact);
                      setSelectedEdge(null);
                    }}
                    className="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-left transition hover:border-blue-200 hover:bg-blue-50"
                  >
                    <span className="truncate text-sm font-semibold text-slate-800">
                      {contact}
                    </span>
                    <span className="shrink-0 rounded-full bg-white px-2 py-1 text-xs font-semibold text-blue-700">
                      {edge.total_records}
                    </span>
                  </button>
                );
              })}

              {selectedNodeEdges.length === 0 && (
                <p className="text-sm text-slate-500">
                  No connected number is available.
                </p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="font-bold text-slate-950">
              Communication distribution
            </h3>
            <div className="mt-4 space-y-3 text-sm">
              {[
                ["Calls", linkDistribution.calls, "bg-blue-500"],
                ["SMS", linkDistribution.sms, "bg-purple-500"],
                ["Calls and SMS", linkDistribution.both, "bg-slate-500"],
              ].map(([label, value, color]) => {
                const percentage = linkDistribution.total
                  ? ((Number(value) / linkDistribution.total) * 100).toFixed(1)
                  : "0.0";

                return (
                  <div key={label}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-slate-600">
                        <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
                        {label}
                      </span>
                      <span className="font-semibold text-slate-900">
                        {percentage}%
                      </span>
                    </div>
                    <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={`h-full rounded-full ${color}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="font-bold text-slate-950">Distance colour code</h3>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Distance is the minimum number of communication relationships
              needed to reach a number from the analysed number. When a number
              can be reached through several paths, the shortest path decides
              its colour.
            </p>
            <div className="mt-4 space-y-2.5">
              {graphModel.distanceLegend.map((item) => (
                <div
                  key={item.key}
                  className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5"
                >
                  <span className="flex min-w-0 items-start gap-2.5">
                    <span
                      className="mt-1 h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-xs leading-5 text-slate-600">
                      {item.label}
                    </span>
                  </span>
                  <span className="shrink-0 rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-700">
                    {item.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
