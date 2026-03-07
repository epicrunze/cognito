import { useState, useRef, useEffect } from "react";

// ─── Tokens ──────────────────────────────────────────────────
const t = {
  bgBase: "#111110", bgSurface: "#1A1A19", bgSurfaceHover: "#222221",
  bgSidebar: "#161615", bgOverlay: "rgba(0,0,0,0.6)", bgElevated: "#252524",
  borderDefault: "#2A2A28", borderStrong: "#3A3A37", borderSubtle: "#1F1F1E",
  textPrimary: "#EDEDEC", textSecondary: "#A1A09A", textTertiary: "#6B6A65", textOnAccent: "#111110",
  accent: "#E8772E", accentHover: "#D4691F", accentSubtle: "rgba(232,119,46,0.1)", accentGlow: "rgba(232,119,46,0.25)",
  priorityUrgent: "#EF5744", priorityHigh: "#E8772E", priorityMedium: "#E2C541",
  priorityLow: "#5BBC6E", priorityNone: "#4A4A46",
  done: "#5BBC6E", overdue: "#EF5744",
  shadowSm: "0 1px 3px rgba(0,0,0,0.3)", shadowMd: "0 4px 12px rgba(0,0,0,0.4)", shadowLg: "0 8px 24px rgba(0,0,0,0.5)",
};
const sans = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif";
const mono = "'IBM Plex Mono', 'Menlo', monospace";

if (!document.getElementById("cog-f")) {
  const l = document.createElement("link"); l.id = "cog-f";
  l.href = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap";
  l.rel = "stylesheet"; document.head.appendChild(l);
}

// ─── Tooltip (positions to right for sidebar) ────────────────
function Tip({ text, children, side = "top" }) {
  const [h, setH] = useState(false);
  const posStyle = side === "right"
    ? { left: "calc(100% + 8px)", top: "50%", transform: "translateY(-50%)" }
    : { bottom: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)" };
  const arrowStyle = side === "right"
    ? { left: -4, top: "50%", transform: "translateY(-50%) rotate(45deg)", borderLeft: `1px solid ${t.borderStrong}`, borderBottom: `1px solid ${t.borderStrong}`, borderRight: "none", borderTop: "none" }
    : { bottom: -4, left: "50%", transform: "translateX(-50%) rotate(45deg)", borderRight: `1px solid ${t.borderStrong}`, borderBottom: `1px solid ${t.borderStrong}`, borderLeft: "none", borderTop: "none" };
  return (
    <span style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}>
      {children}
      {h && <span style={{
        position: "absolute", ...posStyle, background: t.bgElevated, border: `1px solid ${t.borderStrong}`,
        borderRadius: 6, padding: "5px 10px", fontSize: 12, fontFamily: sans, color: t.textSecondary,
        whiteSpace: "nowrap", zIndex: 300, boxShadow: t.shadowMd, animation: "fadeIn 100ms ease-out",
      }}>{text}<span style={{ position: "absolute", width: 7, height: 7, background: t.bgElevated, ...arrowStyle }} /></span>}
    </span>
  );
}

// ─── Button ──────────────────────────────────────────────────
function Button({ children, variant = "accent", size = "md", loading = false, disabled = false, onClick, style: sx }) {
  const [h, setH] = useState(false);
  const s = size === "sm" ? { h: 34, p: "0 14px", fs: 13.5 } : { h: 40, p: "0 18px", fs: 14 };
  const v = {
    accent: { bg: h ? t.accentHover : t.accent, c: t.textOnAccent, b: "none" },
    outline: { bg: h ? t.bgSurfaceHover : "transparent", c: h ? t.textPrimary : t.textSecondary, b: `1px solid ${h ? t.borderStrong : t.borderDefault}` },
    ghost: { bg: h ? t.bgSurfaceHover : "transparent", c: h ? t.textPrimary : t.textSecondary, b: "1px solid transparent" },
    danger: { bg: h ? "#DC2626" : "transparent", c: h ? "#fff" : t.overdue, b: `1px solid ${h ? "#DC2626" : t.borderStrong}` },
    toggle: { bg: h ? t.bgSurfaceHover : t.bgElevated, c: t.textSecondary, b: `1px solid ${t.borderDefault}` },
  }[variant];
  return (
    <button onClick={onClick} disabled={disabled || loading}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{
        height: s.h, padding: s.p, fontSize: s.fs, fontWeight: 500, fontFamily: sans,
        background: v.bg, color: v.c, border: v.b, borderRadius: 8,
        cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.4 : 1,
        display: "inline-flex", alignItems: "center", gap: 7, flexShrink: 0,
        transition: "all 150ms ease-out", lineHeight: 1, letterSpacing: "-0.01em", whiteSpace: "nowrap", ...sx,
      }}>
      {loading && <span style={{ display: "inline-flex", animation: "spin 0.8s linear infinite" }}>
        <svg width={15} height={15} viewBox="0 0 15 15" fill="none">
          <circle cx={7.5} cy={7.5} r={6} stroke="currentColor" strokeWidth={1.5} opacity={0.25} />
          <path d="M13.5 7.5a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" />
        </svg></span>}
      {children}
    </button>
  );
}

// ─── Input ───────────────────────────────────────────────────
function Input({ placeholder = "", value, onChange, style: sx }) {
  const [f, setF] = useState(false);
  return (
    <input type="text" value={value} onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder} onFocus={() => setF(true)} onBlur={() => setF(false)}
      style={{
        height: 34, padding: "0 12px", fontSize: 13.5, fontFamily: sans, fontWeight: 400,
        color: t.textPrimary, background: t.bgElevated,
        border: `1px solid ${f ? t.accent : t.borderDefault}`, borderRadius: 8, outline: "none",
        boxShadow: f ? `0 0 0 2px ${t.accent}25` : "none",
        transition: "all 150ms ease-out", minWidth: 0, ...sx,
      }} />
  );
}

// ─── Textarea ────────────────────────────────────────────────
function Textarea({ placeholder, value, onChange, rows = 3 }) {
  const [f, setF] = useState(false);
  return (
    <textarea value={value} onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder} rows={rows}
      onFocus={() => setF(true)} onBlur={() => setF(false)}
      style={{
        padding: "10px 14px", fontSize: 15, fontFamily: sans, fontWeight: 400,
        color: t.textPrimary, background: t.bgElevated,
        border: `1px solid ${f ? t.accent : t.borderDefault}`, borderRadius: 8, outline: "none",
        boxShadow: f ? `0 0 0 2px ${t.accent}25` : "none",
        transition: "all 150ms ease-out", width: "100%", resize: "vertical", lineHeight: 1.55,
      }} />
  );
}

// ─── Checkbox ────────────────────────────────────────────────
function Checkbox({ checked = false, onChange, size = 20 }) {
  const [h, setH] = useState(false);
  return (
    <button onClick={() => onChange?.(!checked)}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{
        width: size, height: size, borderRadius: "50%",
        border: checked ? "none" : `1.5px solid ${h ? t.textTertiary : t.borderStrong}`,
        background: checked ? t.done : h ? t.bgSurfaceHover : "transparent",
        cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
        transition: "all 200ms ease-out", padding: 0, flexShrink: 0,
      }}>
      {checked && <svg width={11} height={11} viewBox="0 0 11 11" fill="none">
        <path d="M2.5 6L4.5 8L8.5 3.5" stroke={t.bgBase} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" /></svg>}
    </button>
  );
}

function PriorityIndicator({ level = 3, size = "md" }) {
  const ds = size === "sm" ? 7 : 8;
  const c = [t.priorityNone, t.priorityLow, t.priorityLow, t.priorityMedium, t.priorityHigh, t.priorityUrgent];
  return (
    <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
      {[1,2,3,4,5].map(i => <div key={i} style={{ width: ds, height: ds, borderRadius: "50%", background: i <= level ? (c[level]||t.priorityNone) : t.borderDefault, transition: "all 150ms" }} />)}
    </div>
  );
}

// ─── Badge ───────────────────────────────────────────────────
function Badge({ children, color, stats }) {
  const [h, setH] = useState(false);
  const bg = color ? `${color}20` : t.bgElevated; const fg = color || t.textSecondary;
  return (
    <span style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}>
      <span style={{ display: "inline-flex", alignItems: "center", height: 24, padding: "0 9px", fontSize: 12.5, fontWeight: 500, fontFamily: sans, color: fg, background: bg, borderRadius: 9999, lineHeight: 1, whiteSpace: "nowrap", cursor: stats ? "default" : "inherit" }}>{children}</span>
      {stats && h && (
        <div style={{ position: "absolute", bottom: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)", background: t.bgElevated, border: `1px solid ${t.borderStrong}`, borderRadius: 8, padding: "10px 14px", boxShadow: t.shadowMd, zIndex: 200, minWidth: 170, animation: "fadeIn 100ms ease-out" }}>
          <div style={{ fontSize: 13, fontWeight: 600, fontFamily: sans, color: fg, marginBottom: 8 }}>{children}</div>
          {[["Total", stats.total], ["Done", stats.done], ["Open", stats.total - stats.done]].map(([l, v]) => (
            <div key={l} style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, fontFamily: sans, marginBottom: 3 }}>
              <span style={{ color: t.textTertiary }}>{l}</span><span style={{ color: t.textSecondary, fontWeight: 500 }}>{v}</span>
            </div>))}
          <div style={{ height: 1, background: t.borderDefault, margin: "5px 0" }} />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, fontFamily: sans }}>
            <span style={{ color: t.textTertiary }}>Completion</span>
            <span style={{ color: t.done, fontWeight: 500 }}>{Math.round((stats.done / stats.total) * 100)}%</span>
          </div>
          <div style={{ position: "absolute", bottom: -4, left: "50%", transform: "translateX(-50%) rotate(45deg)", width: 7, height: 7, background: t.bgElevated, borderRight: `1px solid ${t.borderStrong}`, borderBottom: `1px solid ${t.borderStrong}` }} />
        </div>
      )}
    </span>
  );
}

function DateDisplay({ date, overdue = false }) {
  return <span style={{ fontSize: 13.5, fontFamily: sans, fontWeight: 400, color: overdue ? t.overdue : t.textTertiary, whiteSpace: "nowrap" }}>{date}</span>;
}
function Kbd({ children }) {
  return <kbd style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", minWidth: 22, height: 22, padding: "0 6px", fontSize: 11.5, fontFamily: mono, fontWeight: 500, color: t.textTertiary, background: t.bgElevated, border: `1px solid ${t.borderDefault}`, borderRadius: 5, lineHeight: 1 }}>{children}</kbd>;
}
function Skeleton({ width = "100%", height = 14, radius = 6 }) {
  return <div style={{ width, height, borderRadius: radius, background: t.bgElevated, animation: "pulse 1.5s ease-in-out infinite" }} />;
}
function Toast({ message, variant = "success", onClose }) {
  const icons = { success: "✓", error: "✕", info: "→" };
  const colors = { success: t.done, error: t.overdue, info: t.accent };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: t.bgSurface, border: `1px solid ${t.borderDefault}`, borderRadius: 8, boxShadow: t.shadowMd, fontSize: 14, fontFamily: sans, color: t.textPrimary, minWidth: 280, animation: "slideUp 200ms ease-out" }}>
      <span style={{ width: 22, height: 22, borderRadius: "50%", background: `${colors[variant]}18`, color: colors[variant], display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>{icons[variant]}</span>
      <span style={{ flex: 1 }}>{message}</span>
      <button onClick={onClose} style={{ background: "none", border: "none", color: t.textTertiary, cursor: "pointer", fontSize: 16, padding: 0, lineHeight: 1 }}>×</button>
    </div>
  );
}

// ─── Dropdown (NEW PRIMITIVE) ────────────────────────────────
function Dropdown({ options, value, onChange, placeholder = "Select...", width = 200 }) {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(null);
  const ref = useRef(null);
  const selected = options.find(o => o.value === value);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex", width }}>
      <button onClick={() => setOpen(!open)} style={{
        width: "100%", height: 34, padding: "0 12px", fontSize: 13.5, fontFamily: sans, fontWeight: 400,
        color: selected ? t.textPrimary : t.textTertiary, background: t.bgElevated,
        border: `1px solid ${open ? t.accent : t.borderDefault}`, borderRadius: 8,
        cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
        transition: "all 150ms ease-out", outline: "none",
        boxShadow: open ? `0 0 0 2px ${t.accent}25` : "none",
      }}>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {selected ? selected.label : placeholder}
        </span>
        <span style={{ fontSize: 10, color: t.textTertiary, marginLeft: 8, transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 150ms" }}>▼</span>
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, width: "100%", zIndex: 300,
          background: t.bgElevated, border: `1px solid ${t.borderStrong}`, borderRadius: 8,
          boxShadow: t.shadowLg, overflow: "hidden", animation: "fadeIn 100ms ease-out",
          padding: "4px",
        }}>
          {options.map((opt) => (
            <button key={opt.value}
              onMouseEnter={() => setHovered(opt.value)} onMouseLeave={() => setHovered(null)}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: "100%", padding: "8px 10px", fontSize: 13.5, fontFamily: sans,
                fontWeight: opt.value === value ? 500 : 400,
                color: opt.value === value ? t.accent : hovered === opt.value ? t.textPrimary : t.textSecondary,
                background: opt.value === value ? t.accentSubtle : hovered === opt.value ? t.bgSurfaceHover : "transparent",
                border: "none", borderRadius: 6, cursor: "pointer",
                display: "flex", flexDirection: "column", gap: 2, textAlign: "left",
                transition: "all 100ms ease-out",
              }}>
              <span>{opt.label}</span>
              {opt.description && <span style={{ fontSize: 12, color: t.textTertiary, fontWeight: 400 }}>{opt.description}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── TaskRow ─────────────────────────────────────────────────
function TaskRow({ title, project, priority, dueDate, labels = [], done = false, overdue = false, selected = false, description, attachments = 0, subtasks, aiTagged = false, viewed = true }) {
  const [hov, setHov] = useState(false);
  const [checked, setChecked] = useState(done);
  const glow = aiTagged && !viewed;
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "grid", gridTemplateColumns: "20px 42px 1fr auto",
        alignItems: "start", gap: 14, padding: "14px 20px",
        background: selected ? t.accentSubtle : hov ? t.bgSurfaceHover : "transparent",
        borderBottom: `1px solid ${t.borderSubtle}`,
        borderLeft: selected ? `2px solid ${t.accent}` : glow ? `2px solid ${t.accent}` : "2px solid transparent",
        boxShadow: glow ? `inset 3px 0 8px -4px ${t.accentGlow}` : "none",
        cursor: "pointer", transition: "all 150ms ease-out", minHeight: 56,
      }}>
      <div style={{ paddingTop: 2 }}><Checkbox checked={checked} onChange={setChecked} /></div>
      <div style={{ paddingTop: 3 }}><PriorityIndicator level={priority} size="sm" /></div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 500, fontFamily: sans, color: checked ? t.textTertiary : t.textPrimary, textDecoration: checked ? "line-through" : "none", lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</div>
        {description && !checked && <div style={{ fontSize: 13, fontFamily: sans, color: t.textTertiary, marginTop: 3, lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "90%" }}>{description}</div>}
        <div style={{ display: "flex", gap: 7, marginTop: 5, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, color: t.textTertiary, fontFamily: sans }}>{project}</span>
          {labels.map((l, i) => <Badge key={i} color={l.color} stats={l.stats}>{l.name}</Badge>)}
          {attachments > 0 && <Tip text={`${attachments} attachment${attachments > 1 ? "s" : ""}`}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 12, color: t.textTertiary }}>
              <svg width={13} height={13} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M13.5 7.5l-5.4 5.4a3.2 3.2 0 01-4.5-4.5l5.4-5.4a2 2 0 012.8 2.8L6.4 11.2a.8.8 0 01-1.1-1.1l4.5-4.5" strokeLinecap="round" /></svg>{attachments}
            </span></Tip>}
          {subtasks && <Tip text={`${subtasks.done} of ${subtasks.total} subtasks complete`}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, color: t.textTertiary }}>
              <svg width={13} height={13} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.5}><rect x={2} y={2} width={5} height={5} rx={1} /><rect x={9} y={9} width={5} height={5} rx={1} /><path d="M4.5 7v2.5h4.5" /></svg>{subtasks.done}/{subtasks.total}
            </span></Tip>}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 2 }}>
        <DateDisplay date={dueDate} overdue={overdue} />
        <span style={{ opacity: hov ? 0.4 : 0, transition: "opacity 150ms", color: t.textTertiary, fontSize: 16 }}>›</span>
      </div>
    </div>
  );
}

// ─── ProposalCard ────────────────────────────────────────────
function ProposalCard({ title, project, priority, dueDate, labels = [], estimate }) {
  const [checked, setChecked] = useState(true);
  const [hov, setHov] = useState(false);
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", gap: 14, padding: "16px 18px", background: t.bgSurface,
        border: `1px solid ${hov ? t.borderStrong : t.borderDefault}`, borderRadius: 10,
        borderLeft: `2px solid ${t.accent}`, boxShadow: hov ? t.shadowSm : `inset 3px 0 8px -4px ${t.accentGlow}`,
        transition: "all 150ms ease-out", alignItems: "flex-start",
      }}>
      <Checkbox checked={checked} onChange={setChecked} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 7 }}>
          <PriorityIndicator level={priority} size="sm" />
          <span style={{ fontSize: 15, fontWeight: 500, fontFamily: sans, color: t.textPrimary, lineHeight: 1.3 }}>{title}</span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, color: t.textTertiary }}>{project}</span>
          <span style={{ fontSize: 13, color: t.borderStrong }}>·</span><DateDisplay date={dueDate} />
          {estimate && <><span style={{ fontSize: 13, color: t.borderStrong }}>·</span><span style={{ fontSize: 13, color: t.textTertiary }}>{estimate}</span></>}
          {labels.map((l, i) => <Badge key={i} color={l.color}>{l.name}</Badge>)}
        </div>
      </div>
      <button style={{ opacity: hov ? 1 : 0, fontSize: 13, fontFamily: sans, fontWeight: 500, color: t.textSecondary, background: "none", border: `1px solid ${t.borderStrong}`, borderRadius: 6, padding: "4px 10px", cursor: "pointer", transition: "opacity 150ms" }}>edit</button>
    </div>
  );
}

function RawResponse({ data }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 16 }}>
      <button onClick={() => setOpen(!open)} style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", color: t.textTertiary, fontSize: 13, fontFamily: sans, cursor: "pointer", padding: 0 }}>
        <span style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 150ms", fontSize: 10 }}>▶</span>Raw AI Response
      </button>
      {open && <pre style={{ marginTop: 10, padding: 16, background: t.bgBase, border: `1px solid ${t.borderDefault}`, borderRadius: 8, fontSize: 12.5, fontFamily: mono, color: t.textSecondary, lineHeight: 1.6, overflow: "auto", maxHeight: 300, whiteSpace: "pre-wrap" }}>{data}</pre>}
    </div>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────
function Sidebar({ activeNav, setActiveNav, collapsed, setCollapsed }) {
  const w = collapsed ? 56 : 240;
  const nav = [
    { id: "all", label: "All Tasks", icon: "☰", count: 12 },
    { id: "upcoming", label: "Upcoming", icon: "◷", count: 5 },
    { id: "overdue", label: "Overdue", icon: "!", count: 2, cc: t.overdue },
  ];
  const projects = [
    { name: "PhD", color: "#E8772E", count: 8 },
    { name: "Admin", color: "#5BBC6E", count: 3 },
    { name: "Teaching", color: "#6B9BD2", count: 1 },
  ];

  return (
    <div style={{ width: w, background: t.bgSidebar, borderRight: `1px solid ${t.borderSubtle}`, display: "flex", flexDirection: "column", padding: collapsed ? "16px 0 12px" : "20px 0", flexShrink: 0, height: "100%", transition: "width 200ms ease-out", overflow: collapsed ? "visible" : "hidden", position: "relative", zIndex: 50 }}>
      {/* Header */}
      <div style={{ padding: collapsed ? "0" : "0 20px", marginBottom: collapsed ? 16 : 28, display: "flex", alignItems: "center", justifyContent: collapsed ? "center" : "space-between" }}>
        {!collapsed && <span style={{ fontSize: 18, fontWeight: 600, fontFamily: sans, color: t.textPrimary, letterSpacing: "-0.03em" }}>cognito</span>}
        <Tip text={collapsed ? "Expand" : "Collapse"} side={collapsed ? "right" : "top"}>
          <button onClick={() => setCollapsed(!collapsed)} style={{ width: 28, height: 28, display: "flex", alignItems: "center", justifyContent: "center", background: "none", border: "none", color: t.textTertiary, cursor: "pointer", borderRadius: 6, fontSize: 14 }}>
            {collapsed ? "»" : "«"}
          </button>
        </Tip>
      </div>

      {/* Nav */}
      <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: collapsed ? "0 8px" : "0 8px" }}>
        {nav.map(item => {
          const active = activeNav === item.id;
          return collapsed ? (
            <Tip key={item.id} text={`${item.label} (${item.count})`} side="right">
              <SNavBtn active={active} onClick={() => setActiveNav(item.id)} center>
                <span style={{ fontSize: 15, color: active ? t.accent : t.textSecondary }}>{item.icon}</span>
              </SNavBtn>
            </Tip>
          ) : (
            <SNavBtn key={item.id} active={active} onClick={() => setActiveNav(item.id)}>
              <span style={{ fontSize: 14, fontFamily: sans, fontWeight: active ? 500 : 400, color: active ? t.accent : t.textSecondary }}>{item.label}</span>
              <span style={{ fontSize: 12, fontFamily: sans, fontWeight: 500, color: item.cc || t.textTertiary, marginLeft: "auto" }}>{item.count}</span>
            </SNavBtn>
          );
        })}
      </div>

      {/* Projects */}
      {!collapsed && <div style={{ padding: "0 20px", marginTop: 28, marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 600, fontFamily: sans, color: t.textTertiary, textTransform: "uppercase", letterSpacing: "0.08em" }}>Projects</span>
      </div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "0 8px", marginTop: collapsed ? 16 : 0 }}>
        {projects.map(p => collapsed ? (
          <Tip key={p.name} text={`${p.name} (${p.count})`} side="right">
            <SNavBtn center>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: p.color }} />
            </SNavBtn>
          </Tip>
        ) : (
          <SNavBtn key={p.name}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: p.color, flexShrink: 0 }} />
            <span style={{ fontSize: 14, fontFamily: sans, color: t.textSecondary, flex: 1, textAlign: "left" }}>{p.name}</span>
            <span style={{ fontSize: 12, fontFamily: sans, color: t.textTertiary }}>{p.count}</span>
          </SNavBtn>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      {/* AI Extract */}
      <div style={{ padding: "0 8px", marginBottom: 4 }}>
        {collapsed ? (
          <Tip text="AI Extract" side="right">
            <SNavBtn center style={{ border: `1px solid ${t.accent}30`, background: t.accentSubtle }}>
              <span style={{ color: t.accent, fontSize: 16, fontWeight: 700 }}>◆</span>
            </SNavBtn>
          </Tip>
        ) : (
          <SNavBtn style={{ border: `1px solid ${t.accent}30`, background: t.accentSubtle }}>
            <span style={{ color: t.accent, fontSize: 14, fontFamily: sans, fontWeight: 600 }}>◆ AI Extract</span>
          </SNavBtn>
        )}
      </div>

      {collapsed ? (
        <div style={{ padding: "0 8px" }}>
          <Tip text="Settings" side="right">
            <SNavBtn center><span style={{ fontSize: 15, color: t.textTertiary }}>⚙</span></SNavBtn>
          </Tip>
        </div>
      ) : (
        <>
          <div style={{ padding: "0 8px" }}><SNavBtn><span style={{ fontSize: 13, fontFamily: sans, color: t.textTertiary }}>Settings</span></SNavBtn></div>
          <div style={{ padding: "12px 20px", marginTop: 8, borderTop: `1px solid ${t.borderSubtle}` }}>
            <span style={{ fontSize: 13, fontFamily: sans, color: t.textTertiary }}>s.martinez@uni.edu</span>
          </div>
        </>
      )}
    </div>
  );
}

function SNavBtn({ children, active, onClick, center, style: sx }) {
  const [h, setH] = useState(false);
  return (
    <button onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: center ? "8px 0" : "8px 12px",
        justifyContent: center ? "center" : "flex-start",
        borderRadius: 7, border: "none",
        background: active ? t.accentSubtle : h ? t.bgSurfaceHover : "transparent",
        cursor: "pointer", transition: "all 100ms ease-out", width: "100%", ...sx,
      }}>{children}</button>
  );
}

// ─── Tag stats ───────────────────────────────────────────────
const tagStats = { ethics: { total: 4, done: 2 }, admin: { total: 6, done: 3 }, writing: { total: 8, done: 5 }, presentation: { total: 3, done: 1 }, grading: { total: 5, done: 4 }, booking: { total: 2, done: 2 } };

const modelOptions = [
  { value: "gemini-flash", label: "Gemini 2.0 Flash", description: "Fast, good for most tasks" },
  { value: "gemini-pro", label: "Gemini 2.0 Pro", description: "Higher quality, slower" },
  { value: "ollama-qwen", label: "Qwen 3.x (Local)", description: "Private, runs on your machine" },
  { value: "ollama-llama", label: "Llama 3.3 (Local)", description: "Private, larger model" },
];

// ─── Main ────────────────────────────────────────────────────
export default function App() {
  const [inputVal, setInputVal] = useState("");
  const [textareaVal, setTextareaVal] = useState("");
  const [showToasts, setShowToasts] = useState(false);
  const [activeSection, setActiveSection] = useState("app");
  const [activeNav, setActiveNav] = useState("all");
  const [collapsed, setCollapsed] = useState(false);
  const [localProcessing, setLocalProcessing] = useState(false);
  const [showCompleted, setShowCompleted] = useState(true);
  const [selectedModel, setSelectedModel] = useState("gemini-flash");
  const [dropdownDemo, setDropdownDemo] = useState("gemini-flash");

  const rawAI = `{
  "model": "${selectedModel}",
  "tool_calls": [
    {"name": "lookup_projects", "args": {}},
    {"name": "resolve_project", "args": {"name": "PhD"}},
    {"name": "resolve_project", "args": {"name": "Admin"}},
    {"name": "check_existing_tasks", "args": {"title": "Book room"}}
  ],
  "proposals": [
    {
      "title": "Revise chapter 3",
      "project_id": 1, "priority": 4, "due_date": "2026-03-07",
      "labels": ["writing"],
      "auto_tag_reason": "Matched 'writing': drafting, revision, or editing of thesis chapters"
    },
    {
      "title": "Prepare lab meeting presentation",
      "project_id": 1, "priority": 3, "due_date": "2026-03-10",
      "labels": ["presentation"],
      "auto_tag_reason": "Matched 'presentation': slide decks, talks, demo prep"
    },
    {
      "title": "Book room for lab meeting",
      "project_id": 2, "priority": 2, "due_date": "2026-03-08",
      "labels": ["booking"],
      "auto_tag_reason": "Matched 'booking': room reservations, equipment bookings"
    }
  ],
  "tokens_used": 1247, "latency_ms": 890
}`;

  return (
    <div style={{ background: t.bgBase, minHeight: "100vh", fontFamily: sans, color: t.textPrimary }}>
      <style>{`
        @keyframes pulse{0%,100%{opacity:.4}50%{opacity:.8}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes slideUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        @keyframes fadeIn{from{opacity:0}to{opacity:1}}
        *{box-sizing:border-box;margin:0}
        ::placeholder{color:${t.textTertiary}}
        ::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:${t.borderDefault};border-radius:3px}
      `}</style>

      {/* Top tabs */}
      <div style={{ display: "flex", gap: 2, padding: "12px 24px", borderBottom: `1px solid ${t.borderSubtle}`, background: t.bgSurface }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center" }}>
          <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.03em" }}>cognito</span>
          <span style={{ fontSize: 13, color: t.textTertiary, marginLeft: 12 }}>design system</span>
        </div>
        {["app", "primitives", "extraction"].map(s => (
          <TabBtn key={s} active={activeSection === s} onClick={() => setActiveSection(s)}>
            {s === "app" ? "App Preview" : s.charAt(0).toUpperCase() + s.slice(1)}
          </TabBtn>
        ))}
      </div>

      {/* ═══ APP ═══ */}
      {activeSection === "app" && (
        <div style={{ display: "flex", height: "calc(100vh - 50px)" }}>
          <Sidebar activeNav={activeNav} setActiveNav={setActiveNav} collapsed={collapsed} setCollapsed={setCollapsed} />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
            {/* Top bar — fixed single row */}
            <div style={{ display: "flex", alignItems: "center", padding: "10px 24px", borderBottom: `1px solid ${t.borderSubtle}`, gap: 10, flexShrink: 0 }}>
              <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.02em", flexShrink: 0, marginRight: "auto" }}>All Tasks</span>
              <Input placeholder="Search..." value="" onChange={() => {}} style={{ width: 180, flexShrink: 1 }} />
              <Button variant="outline" size="sm">Filter</Button>
              <Button variant="accent" size="sm">◆ Extract</Button>
              <Button variant="accent" size="sm">+ New</Button>
            </div>

            {/* Quick add */}
            <div style={{ padding: "11px 24px", color: t.textTertiary, fontSize: 15, borderBottom: `1px solid ${t.borderSubtle}`, cursor: "text", flexShrink: 0 }}>
              <span style={{ opacity: 0.5 }}>+</span><span style={{ marginLeft: 10 }}>Add task...</span>
            </div>

            <div style={{ flex: 1, overflowY: "auto" }}>
              <TaskRow title="Submit ethics amendment" project="PhD" priority={5} dueDate="Mar 3" overdue
                description="Final submission to ethics board — deadline extended from Feb 28"
                labels={[{ name: "ethics", color: "#5BBC6E", stats: tagStats.ethics }, { name: "admin", color: "#E8772E", stats: tagStats.admin }]}
                attachments={2} subtasks={{ done: 3, total: 5 }} selected />
              <TaskRow title="Revise chapter 3" project="PhD" priority={4} dueDate="Mar 7"
                description="Full revision based on supervisor feedback"
                labels={[{ name: "writing", color: "#6B9BD2", stats: tagStats.writing }]}
                subtasks={{ done: 1, total: 4 }} aiTagged viewed={false} />
              <TaskRow title="Prepare lab meeting presentation" project="PhD" priority={3} dueDate="Mar 10"
                labels={[{ name: "presentation", color: "#A78BFA", stats: tagStats.presentation }]} attachments={1} />
              <TaskRow title="Email supervisor about extension" project="PhD" priority={2} dueDate="Mar 12" />
              <TaskRow title="Grade midterm papers" project="Teaching" priority={3} dueDate="Mar 14"
                description="30 papers, use rubric from last semester"
                labels={[{ name: "grading", color: "#E2C541", stats: tagStats.grading }]} subtasks={{ done: 12, total: 30 }} />

              {/* Completed divider */}
              <button onClick={() => setShowCompleted(!showCompleted)} style={{
                display: "flex", alignItems: "center", gap: 10, padding: "16px 24px", width: "100%",
                color: t.textTertiary, fontSize: 13, fontFamily: sans, background: "none", border: "none", cursor: "pointer",
              }}>
                <span style={{ flex: 1, height: 1, background: t.borderDefault }} />
                <span>Completed (2)</span>
                <span style={{ fontSize: 10, transition: "transform 150ms", transform: showCompleted ? "rotate(180deg)" : "rotate(0deg)" }}>▼</span>
                <span style={{ flex: 1, height: 1, background: t.borderDefault }} />
              </button>
              {showCompleted && <div style={{ opacity: 0.65 }}>
                <TaskRow title="Book room for lab meeting" project="Admin" priority={2} dueDate="Mar 8" done labels={[{ name: "booking", color: "#A78BFA", stats: tagStats.booking }]} />
                <TaskRow title="Order lab supplies" project="Admin" priority={1} dueDate="Mar 15" done />
              </div>}
            </div>
          </div>
        </div>
      )}

      {/* ═══ PRIMITIVES ═══ */}
      {activeSection === "primitives" && (
        <div style={{ maxWidth: 720, margin: "0 auto", padding: "40px 24px", display: "flex", flexDirection: "column", gap: 48 }}>
          <Sec title="Buttons">
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <Button>Approve All</Button>
              <Button>◆ Extract</Button>
              <Button variant="outline">Cancel</Button>
              <Button variant="ghost">Settings</Button>
              <Button variant="danger" size="sm">Delete</Button>
              <Button variant="toggle" size="sm">🔒 Local</Button>
              <Button size="sm">Small</Button>
              <Button loading>Saving</Button>
              <Button disabled>Disabled</Button>
            </div>
          </Sec>

          <Sec title="Dropdown">
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: 13, color: t.textTertiary, marginBottom: 8 }}>Model selector</div>
                <Dropdown options={modelOptions} value={dropdownDemo} onChange={setDropdownDemo} width={220} />
              </div>
              <div>
                <div style={{ fontSize: 13, color: t.textTertiary, marginBottom: 8 }}>Sort by</div>
                <Dropdown options={[
                  { value: "priority", label: "Priority" },
                  { value: "due", label: "Due date" },
                  { value: "created", label: "Created" },
                  { value: "alpha", label: "Alphabetical" },
                ]} value="priority" onChange={() => {}} width={160} placeholder="Sort by..." />
              </div>
            </div>
          </Sec>

          <Sec title="Input & Textarea">
            <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 400 }}>
              <Input placeholder="Add a task..." value={inputVal} onChange={setInputVal} style={{ height: 40, fontSize: 15 }} />
              <Textarea placeholder="Write a description..." value={textareaVal} onChange={setTextareaVal} rows={3} />
            </div>
          </Sec>

          <Sec title="Checkbox & Priority">
            <div style={{ display: "flex", gap: 32, alignItems: "center", flexWrap: "wrap" }}>
              <R><Checkbox /><L>Unchecked</L></R>
              <R><Checkbox checked /><L>Done</L></R>
              <div style={{ width: 1, height: 24, background: t.borderDefault }} />
              {[1,3,5].map(p => <R key={p}><PriorityIndicator level={p} /><span style={{ fontSize: 13, color: t.textTertiary, fontFamily: mono }}>{["","low","","med","","urgent"][p]}</span></R>)}
            </div>
          </Sec>

          <Sec title="Badges (hover for stats)">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Badge color="#5BBC6E" stats={tagStats.ethics}>ethics</Badge>
              <Badge color="#E8772E" stats={tagStats.admin}>admin</Badge>
              <Badge color="#6B9BD2" stats={tagStats.writing}>writing</Badge>
              <Badge color="#A78BFA" stats={tagStats.presentation}>presentation</Badge>
              <Badge color="#E2C541" stats={tagStats.grading}>grading</Badge>
              <Badge color="#EF5744">urgent</Badge>
              <Badge>untagged</Badge>
            </div>
          </Sec>

          <Sec title="AI-tagged indicator">
            <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 520 }}>
              <div style={{ padding: "14px 18px", background: t.bgSurface, borderRadius: 10, border: `1px solid ${t.borderDefault}`, borderLeft: `2px solid ${t.accent}`, boxShadow: `inset 3px 0 8px -4px ${t.accentGlow}` }}>
                <div style={{ fontSize: 14, fontFamily: sans, color: t.textPrimary, fontWeight: 500 }}>Unviewed — orange border + glow</div>
                <div style={{ fontSize: 13, fontFamily: sans, color: t.textTertiary, marginTop: 4 }}>Fades to default after the user opens/views the task</div>
              </div>
              <div style={{ padding: "14px 18px", background: t.bgSurface, borderRadius: 10, border: `1px solid ${t.borderDefault}`, borderLeft: "2px solid transparent" }}>
                <div style={{ fontSize: 14, fontFamily: sans, color: t.textPrimary, fontWeight: 500 }}>Viewed — standard appearance</div>
              </div>
            </div>
          </Sec>

          <Sec title="Keyboard Shortcuts">
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              {[["N","New"],["E","Edit"],["X","Done"],["/","Search"],["Ctrl+↵","Submit"],["Esc","Close"],["J","Down"],["K","Up"]].map(([k,l]) =>
                <R key={k}><Kbd>{k}</Kbd><span style={{ fontSize: 13, color: t.textTertiary }}>{l}</span></R>
              )}
            </div>
          </Sec>

          <Sec title="Skeleton Loading">
            <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 520 }}>
              {[.65,.45,.75].map((w,i) => (
                <div key={i} style={{ display: "flex", gap: 14, alignItems: "center" }}>
                  <Skeleton width={20} height={20} radius={10} /><Skeleton width={42} height={8} />
                  <div style={{ flex: 1 }}><Skeleton width={`${w*100}%`} height={15} /><div style={{ height: 6 }} /><Skeleton width="40%" height={10} /></div>
                  <Skeleton width={52} height={13} />
                </div>
              ))}
            </div>
          </Sec>

          <Sec title="Toast Notifications">
            <Button variant="outline" size="sm" onClick={() => setShowToasts(!showToasts)}>{showToasts ? "Hide" : "Show"} Toasts</Button>
            {showToasts && <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16, maxWidth: 380 }}>
              <Toast message="3 tasks created" variant="success" onClose={() => {}} />
              <Toast message="Failed to update task" variant="error" onClose={() => {}} />
              <Toast message="Extracting tasks..." variant="info" onClose={() => {}} />
            </div>}
          </Sec>
        </div>
      )}

      {/* ═══ EXTRACTION ═══ */}
      {activeSection === "extraction" && (
        <div style={{ maxWidth: 720, margin: "0 auto", padding: "40px 24px", display: "flex", flexDirection: "column", gap: 24 }}>
          <Sec title="AI Task Extraction">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
              <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.02em", color: t.accent }}>◆ Extract Tasks</span>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <Dropdown options={modelOptions} value={selectedModel} onChange={setSelectedModel} width={210} />
                <Button variant="toggle" size="sm" onClick={() => setLocalProcessing(!localProcessing)}
                  style={localProcessing ? { background: t.accentSubtle, borderColor: `${t.accent}40`, color: t.accent } : {}}>
                  {localProcessing ? "🔒 Local" : "🔓 Cloud"}
                </Button>
              </div>
            </div>

            {localProcessing && <div style={{ padding: "10px 16px", marginBottom: 16, borderRadius: 8, background: t.accentSubtle, border: `1px solid ${t.accent}25`, fontSize: 13, fontFamily: sans, color: t.accent }}>
              Processing locally via Ollama — your data stays on this device
            </div>}

            <Textarea placeholder="Paste meeting notes, an email, or describe what needs doing..." rows={4}
              value="I had a meeting with my supervisor today. We agreed I need to revise chapter 3 by next Friday and she wants me to present at the lab meeting on March 10. Oh and I need to book a room for that."
              onChange={() => {}} />
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 14, gap: 10, alignItems: "center" }}>
              <Kbd>Ctrl+↵</Kbd>
              <Button>◆ Extract Tasks</Button>
            </div>

            <RawResponse data={rawAI} />

            <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "24px 0 16px", color: t.textTertiary, fontSize: 13 }}>
              <span style={{ height: 1, width: 20, background: t.borderDefault }} />Extracted 3 tasks<span style={{ flex: 1, height: 1, background: t.borderDefault }} />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <ProposalCard title="Revise chapter 3" project="PhD" priority={4} dueDate="Mar 7" estimate="3h" labels={[{ name: "writing", color: "#6B9BD2" }]} />
              <ProposalCard title="Prepare lab meeting presentation" project="PhD" priority={3} dueDate="Mar 10" estimate="2h" labels={[{ name: "presentation", color: "#A78BFA" }]} />
              <ProposalCard title="Book room for lab meeting" project="Admin" priority={2} dueDate="Mar 8" estimate="10m" labels={[{ name: "booking", color: "#A78BFA" }]} />
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
              <Button variant="ghost" size="sm">Reject Selected</Button>
              <Button>Approve All (3)</Button>
            </div>
          </Sec>
        </div>
      )}
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────
function Sec({ title, children }) {
  return <div><div style={{ fontSize: 11.5, fontWeight: 600, fontFamily: sans, color: t.textTertiary, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 18 }}>{title}</div>{children}</div>;
}
function R({ children }) { return <div style={{ display: "flex", alignItems: "center", gap: 8 }}>{children}</div>; }
function L({ children }) { return <span style={{ fontSize: 14, color: t.textSecondary }}>{children}</span>; }
function TabBtn({ children, active, onClick }) {
  const [h, setH] = useState(false);
  return <button onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
    style={{ padding: "7px 14px", fontSize: 13.5, fontFamily: sans, fontWeight: 500, color: active ? t.accent : h ? t.textPrimary : t.textSecondary, background: active ? t.accentSubtle : h ? t.bgSurfaceHover : "transparent", border: "none", borderRadius: 7, cursor: "pointer", transition: "all 150ms ease-out" }}>{children}</button>;
}
