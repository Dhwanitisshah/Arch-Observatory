import { useEffect, useRef } from "react";
import * as d3 from "d3";

const MIN_RADIUS = 6;
const MAX_RADIUS = 28;
const NO_SMELL_COLOR = "#94a3b8";
const EDGE_COLOR = "#64748b";
const CYCLE_EDGE_COLOR = "#ef4444";
const SELECTED_STROKE = "#38bdf8";

const severityColor = d3.scaleThreshold().domain([25, 50, 75]).range(["#22c55e", "#eab308", "#f97316", "#ef4444"]);

function cycleMemberSets(smells) {
  return (smells || [])
    .filter((s) => s.type === "cyclic_dependency")
    .map((s) => new Set(s.metrics?.members?.length ? s.metrics.members : s.target.split(",").map((m) => m.trim())));
}

function smellsByModule(smells) {
  const map = new Map();
  const add = (module, smell) => {
    if (!module) return;
    if (!map.has(module)) map.set(module, []);
    map.get(module).push(smell);
  };
  for (const s of smells || []) {
    if (s.type === "cyclic_dependency") {
      const members = s.metrics?.members?.length ? s.metrics.members : s.target.split(",").map((m) => m.trim());
      members.forEach((m) => add(m, s));
    } else if (s.type === "complexity_hotspot") {
      add(s.target.split("::")[0], s);
    } else {
      add(s.target, s);
    }
  }
  return map;
}

function worstSeverityByModule(smellsMap) {
  const map = new Map();
  for (const [module, moduleSmells] of smellsMap) {
    map.set(module, Math.max(...moduleSmells.map((s) => s.severity)));
  }
  return map;
}

export default function DependencyGraph({ nodes, edges, smells, selectedModule, onSelectNode }) {
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const tooltipRef = useRef(null);
  const onSelectNodeRef = useRef(onSelectNode);
  const highlightRef = useRef(() => {});

  onSelectNodeRef.current = onSelectNode;

  useEffect(() => {
    if (!nodes || nodes.length === 0) return undefined;

    const width = containerRef.current?.clientWidth || 900;
    const height = containerRef.current?.clientHeight || 600;

    const smellsMap = smellsByModule(smells);
    const worstSeverity = worstSeverityByModule(smellsMap);
    const cycleSets = cycleMemberSets(smells);

    const maxCoupling = Math.max(1, d3.max(nodes, (n) => n.ca + n.ce) || 1);
    const radiusScale = d3.scaleSqrt().domain([0, maxCoupling]).range([MIN_RADIUS, MAX_RADIUS]).clamp(true);

    const nodeIds = new Set(nodes.map((n) => n.module));
    const simNodes = nodes.map((n) => ({ ...n }));
    const simLinks = (edges || [])
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({ ...e }));

    const isCycleEdge = (link) => {
      const s = typeof link.source === "object" ? link.source.module : link.source;
      const t = typeof link.target === "object" ? link.target.module : link.target;
      return cycleSets.some((set) => set.has(s) && set.has(t));
    };

    const neighbors = new Map();
    simLinks.forEach((l) => {
      const s = typeof l.source === "object" ? l.source.module : l.source;
      const t = typeof l.target === "object" ? l.target.module : l.target;
      if (!neighbors.has(s)) neighbors.set(s, new Set());
      if (!neighbors.has(t)) neighbors.set(t, new Set());
      neighbors.get(s).add(t);
      neighbors.get(t).add(s);
    });

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", [0, 0, width, height]).style("width", "100%").style("height", "100%");

    const defs = svg.append("defs");
    [
      ["arrow", EDGE_COLOR],
      ["arrow-cycle", CYCLE_EDGE_COLOR],
    ].forEach(([id, color]) => {
      defs
        .append("marker")
        .attr("id", id)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 16)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", color);
    });

    const zoomLayer = svg.append("g");
    svg.call(
      d3
        .zoom()
        .scaleExtent([0.15, 4])
        .on("zoom", (event) => zoomLayer.attr("transform", event.transform))
    );

    const linkSel = zoomLayer
      .append("g")
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke", (d) => (isCycleEdge(d) ? CYCLE_EDGE_COLOR : EDGE_COLOR))
      .attr("stroke-width", (d) => (isCycleEdge(d) ? 2.5 : 1))
      .attr("stroke-opacity", 0.6)
      .attr("marker-end", (d) => `url(#${isCycleEdge(d) ? "arrow-cycle" : "arrow"})`);

    const nodeGroup = zoomLayer
      .append("g")
      .selectAll("g")
      .data(simNodes, (d) => d.module)
      .join("g")
      .style("cursor", "pointer");

    nodeGroup
      .append("circle")
      .attr("r", (d) => radiusScale(d.ca + d.ce))
      .attr("fill", (d) => {
        const sev = worstSeverity.get(d.module);
        return sev === undefined ? NO_SMELL_COLOR : severityColor(sev);
      })
      .attr("stroke", "#0f172a")
      .attr("stroke-width", 1.5);

    nodeGroup
      .append("text")
      .text((d) => d.module.split(".").pop())
      .attr("font-size", 10)
      .attr("dx", (d) => radiusScale(d.ca + d.ce) + 4)
      .attr("dy", 4)
      .attr("fill", "#e2e8f0")
      .style("pointer-events", "none")
      .style("user-select", "none");

    const tooltip = d3.select(tooltipRef.current);

    nodeGroup
      .on("mouseenter", (_event, d) => {
        const nodeSmells = smellsMap.get(d.module) || [];
        tooltip.style("opacity", 1).html(
          `<strong>${d.module}</strong><br/>` +
            `Ca: ${d.ca} &middot; Ce: ${d.ce} &middot; Instability: ${d.instability.toFixed(2)}<br/>` +
            (nodeSmells.length
              ? nodeSmells.map((s) => `&bull; ${s.title}`).join("<br/>")
              : "No smells detected")
        );
      })
      .on("mousemove", (event) => {
        const [x, y] = d3.pointer(event, containerRef.current);
        tooltip.style("left", `${x + 14}px`).style("top", `${y + 14}px`);
      })
      .on("mouseleave", () => tooltip.style("opacity", 0))
      .on("click", (_event, d) => onSelectNodeRef.current?.(d.module));

    const simulation = d3
      .forceSimulation(simNodes)
      .force("charge", d3.forceManyBody().strength(-220))
      .force(
        "link",
        d3
          .forceLink(simLinks)
          .id((d) => d.module)
          .distance(70)
          .strength(0.4)
      )
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collide",
        d3.forceCollide().radius((d) => radiusScale(d.ca + d.ce) + 8)
      )
      .on("tick", () => {
        linkSel
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);
        nodeGroup.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

    nodeGroup.call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    );

    highlightRef.current = (module) => {
      if (!module) {
        nodeGroup.attr("opacity", 1);
        linkSel.attr("stroke-opacity", (d) => (isCycleEdge(d) ? 0.8 : 0.6));
        nodeGroup.select("circle").attr("stroke", "#0f172a").attr("stroke-width", 1.5);
        return;
      }
      const neighborSet = neighbors.get(module) || new Set();
      nodeGroup.attr("opacity", (d) => (d.module === module || neighborSet.has(d.module) ? 1 : 0.15));
      nodeGroup
        .select("circle")
        .attr("stroke", (d) => (d.module === module ? SELECTED_STROKE : "#0f172a"))
        .attr("stroke-width", (d) => (d.module === module ? 3 : 1.5));
      linkSel.attr("stroke-opacity", (d) => {
        const s = typeof d.source === "object" ? d.source.module : d.source;
        const t = typeof d.target === "object" ? d.target.module : d.target;
        return s === module || t === module ? 0.9 : 0.05;
      });
    };
    highlightRef.current(selectedModule);

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, smells]);

  useEffect(() => {
    highlightRef.current(selectedModule);
  }, [selectedModule]);

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%", height: "100%" }}>
      <svg ref={svgRef} />
      <div
        ref={tooltipRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          pointerEvents: "none",
          opacity: 0,
          background: "rgba(15, 23, 42, 0.95)",
          color: "#e2e8f0",
          padding: "6px 10px",
          borderRadius: 6,
          fontSize: 12,
          lineHeight: 1.4,
          maxWidth: 280,
          transition: "opacity 0.1s ease",
          zIndex: 10,
        }}
      />
    </div>
  );
}
