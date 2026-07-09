import { Fragment, useMemo, useState } from "react";
import { SMELL_ICONS, SMELL_LABELS, moduleFromSmell, severityColor, smellMatchesModule } from "../lib/smellUtils";
import FixPanel from "./FixPanel";

function smellKey(s, i) {
  return `${s.type}-${s.target}-${i}`;
}

export default function SmellTable({ smells, selectedModule, onSelectModule, runId }) {
  const [sort, setSort] = useState({ key: "severity", dir: "desc" });
  const [expandedKey, setExpandedKey] = useState(null);
  const [fixCache, setFixCache] = useState({});

  const filtered = useMemo(
    () => (selectedModule ? smells.filter((s) => smellMatchesModule(s, selectedModule)) : smells),
    [smells, selectedModule]
  );

  const sorted = useMemo(() => {
    const rows = [...filtered];
    const { key, dir } = sort;
    rows.sort((a, b) => {
      let av = key === "target" ? a.target : key === "type" ? a.type : a.severity;
      let bv = key === "target" ? b.target : key === "type" ? b.type : b.severity;
      if (typeof av === "string") av = av.toLowerCase();
      if (typeof bv === "string") bv = bv.toLowerCase();
      if (av < bv) return dir === "asc" ? -1 : 1;
      if (av > bv) return dir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [filtered, sort]);

  function toggleSort(key) {
    setSort((prev) => (prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "severity" ? "desc" : "asc" }));
  }

  function sortIndicator(key) {
    if (sort.key !== key) return "";
    return sort.dir === "asc" ? " ↑" : " ↓";
  }

  return (
    <div className="table-pane">
      <div className="smell-table-header">
        <h3>Smells ({sorted.length})</h3>
        {selectedModule && (
          <span className="smell-filter-note">
            Filtered to {selectedModule}
            <button type="button" className="btn btn-ghost" onClick={() => onSelectModule(null)}>
              Clear
            </button>
          </span>
        )}
      </div>
      <div className="smell-table-scroll">
        {sorted.length === 0 ? (
          <div className="empty-state">No smells for this selection.</div>
        ) : (
          <table className="smell-table">
            <thead>
              <tr>
                <th onClick={() => toggleSort("severity")}>Severity{sortIndicator("severity")}</th>
                <th onClick={() => toggleSort("type")}>Type{sortIndicator("type")}</th>
                <th onClick={() => toggleSort("target")}>Target{sortIndicator("target")}</th>
                <th>Detail</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, i) => {
                const module = moduleFromSmell(s);
                const isSelected = module === selectedModule;
                const color = severityColor(s.severity);
                const key = smellKey(s, i);
                const isExpanded = expandedKey === key;
                return (
                  <Fragment key={key}>
                    <tr
                      className={isSelected ? "selected" : ""}
                      onClick={() => onSelectModule(module)}
                    >
                      <td>
                        <div className="severity-cell">
                          <div className="severity-bar">
                            <div
                              className="severity-bar-fill"
                              style={{ width: `${Math.round(s.severity)}%`, background: color }}
                            />
                          </div>
                          <span style={{ color }}>{Math.round(s.severity)}</span>
                        </div>
                      </td>
                      <td>
                        <div className="type-cell">
                          <span className="type-icon">{SMELL_ICONS[s.type]}</span>
                          <span>{SMELL_LABELS[s.type] || s.type}</span>
                        </div>
                      </td>
                      <td className="target-cell">{s.target}</td>
                      <td className="detail-cell">{s.detail}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedKey(isExpanded ? null : key);
                          }}
                        >
                          {isExpanded ? "Hide fix" : "Fix"}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="fix-row">
                        <td colSpan={5}>
                          <FixPanel
                            runId={runId}
                            smell={s}
                            cacheEntry={fixCache[key]}
                            onResult={(entry) => setFixCache((prev) => ({ ...prev, [key]: entry }))}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
