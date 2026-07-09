export const SMELL_TYPES = ["god_class", "complexity_hotspot", "cyclic_dependency", "painful_coupling"];

export const SMELL_LABELS = {
  god_class: "God class",
  complexity_hotspot: "Complexity hotspot",
  cyclic_dependency: "Cyclic dependency",
  painful_coupling: "Painful coupling",
};

export const SMELL_ICONS = {
  god_class: "■",
  complexity_hotspot: "▲",
  cyclic_dependency: "↻",
  painful_coupling: "⇄",
};

export function severityColor(severity) {
  if (severity >= 75) return "#ef4444";
  if (severity >= 50) return "#f97316";
  if (severity >= 25) return "#eab308";
  return "#22c55e";
}

// A cyclic_dependency smell's target is a comma-separated member list rather
// than a single module — pick the first member as the representative module
// so it still participates in graph/table cross-linking.
export function moduleFromSmell(smell) {
  const target = smell.target || "";
  if (smell.type === "cyclic_dependency") {
    const members = smell.metrics?.members?.length ? smell.metrics.members : target.split(",").map((m) => m.trim());
    return members[0];
  }
  return target.split("::")[0];
}

export function smellMatchesModule(smell, module) {
  if (!module) return true;
  if (smell.type === "cyclic_dependency") {
    const members = smell.metrics?.members?.length
      ? smell.metrics.members
      : (smell.target || "").split(",").map((m) => m.trim());
    return members.includes(module);
  }
  return (smell.target || "").split("::")[0] === module;
}
