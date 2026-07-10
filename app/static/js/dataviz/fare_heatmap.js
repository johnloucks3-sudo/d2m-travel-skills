/**
 * D2M Fare Comparison Heatmap
 * Component 2 of docs/DATAVIZ_FLIGHT_CHARTS_SPEC_20260710.md
 *
 * Form: sequential magnitude grid (carrier x cabin x date-range -> price).
 * Color: ONE hue (D2M navy), light->dark = cheap->expensive. Validated
 * (ordinal ramp, light + dark mode) via the dataviz skill's validate_palette.js
 * — see the spec doc for the exact `node` invocations and PASS output.
 *
 * Usage:
 *   D2MFareHeatmap.render(containerEl, {
 *     rows: ["Business", "Premium Economy"],        // cabins (or carriers)
 *     cols: ["2027-04-28", "2027-04-30", ...],        // dates
 *     rowLabel: "Cabin", colLabel: "Departure date",
 *     cells: [ { row: "Business", col: "2027-04-30", price: 5024, meta: "DEN-VCE, Cruise fare" }, ... ],
 *     currency: "$",
 *     mode: "light" | "dark"   // default "light"
 *   });
 *
 * No dependencies. Ships its own <style> once per page. Renders a table
 * underneath every visual grid (accessibility requirement — table view
 * always exists, not just on toggle) plus a light/dark-aware legend.
 */
(function (global) {
  "use strict";

  // Sequential ramp — light -> dark, single hue (navy), each mode
  // independently validated against its own chart surface.
  const RAMP = {
    light: ["#7ba8cc", "#5f88bb", "#3d6ea5", "#1f4f93", "#003087"],
    dark: ["#eaf2fa", "#b9d3ea", "#7ba8cc", "#4877c9", "#2f5aa8"],
  };
  const SURFACE = { light: "#f7f3ea", dark: "#1a1a1a" };
  const TEXT = {
    light: { primary: "#1a1a1a", muted: "#666666" },
    dark: { primary: "#f7f3ea", muted: "#b0a898" },
  };

  let styleInjected = false;
  function injectStyle() {
    if (styleInjected) return;
    styleInjected = true;
    const css = `
.d2m-heatmap-wrap { font-family: Georgia, serif; }
.d2m-heatmap-wrap table.d2m-heatmap-grid { border-collapse: collapse; width: 100%; }
.d2m-heatmap-wrap table.d2m-heatmap-grid th, .d2m-heatmap-wrap table.d2m-heatmap-grid td {
  padding: 8px 10px; text-align: center; font-size: 13px; border: 2px solid var(--d2m-surface, #f7f3ea);
}
.d2m-heatmap-wrap table.d2m-heatmap-grid th { font-weight: bold; font-size: 12px; }
.d2m-heatmap-wrap th.d2m-row-head { text-align: right; white-space: nowrap; }
.d2m-heatmap-wrap td.d2m-cell { font-variant-numeric: tabular-nums; font-weight: 600; cursor: default; position: relative; }
.d2m-heatmap-wrap td.d2m-cell:hover { outline: 2px solid; outline-offset: -2px; }
.d2m-heatmap-wrap td.d2m-cell-empty { background: transparent !important; color: var(--d2m-muted, #666); font-style: italic; font-weight: normal; font-size: 12px; }
.d2m-heatmap-legend { display: flex; align-items: center; gap: 6px; margin: 10px 0; font-size: 11px; }
.d2m-heatmap-legend .d2m-swatch { width: 22px; height: 12px; display: inline-block; border-radius: 2px; }
.d2m-heatmap-legend .d2m-legend-label { margin: 0 8px; }
.d2m-heatmap-tooltip {
  position: fixed; pointer-events: none; z-index: 9999; font-family: Georgia, serif; font-size: 12px;
  background: #02021e; color: #f0f5ff; padding: 6px 10px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,.3);
  display: none; max-width: 260px;
}
.d2m-heatmap-tableview { margin-top: 14px; font-size: 12px; }
.d2m-heatmap-tableview summary { cursor: pointer; color: var(--d2m-navy, #003087); font-weight: bold; }
.d2m-heatmap-tableview table { border-collapse: collapse; width: 100%; margin-top: 8px; }
.d2m-heatmap-tableview th, .d2m-heatmap-tableview td { border-bottom: 1px solid #ddd; padding: 5px 8px; text-align: left; }
`;
    const el = document.createElement("style");
    el.setAttribute("data-d2m-heatmap", "1");
    el.textContent = css;
    document.head.appendChild(el);
  }

  function contrastText(hex, mode) {
    // crude luminance check to decide white vs dark text on a fill
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    if (mode === "dark") return lum > 0.55 ? "#1a1a1a" : "#f7f3ea";
    return lum > 0.55 ? "#1a1a1a" : "#ffffff";
  }

  function priceToStep(price, min, max, steps) {
    if (max === min) return 0;
    const t = (price - min) / (max - min);
    return Math.max(0, Math.min(steps - 1, Math.round(t * (steps - 1))));
  }

  // Safe element builder — never touches innerHTML with data-derived strings,
  // so a stray "<" in a fare note/label can never be interpreted as markup.
  function el(tag, props, children) {
    const node = document.createElement(tag);
    if (props) {
      Object.keys(props).forEach((k) => {
        if (k === "text") node.textContent = props[k];
        else if (k === "style") Object.assign(node.style, props[k]);
        else if (k.startsWith("data-") || k === "tabindex" || k === "aria-label") {
          node.setAttribute(k, props[k]);
        } else {
          node[k] = props[k];
        }
      });
    }
    (children || []).forEach((c) => node.appendChild(c));
    return node;
  }

  function render(container, opts) {
    injectStyle();
    const mode = opts.mode === "dark" ? "dark" : "light";
    const ramp = RAMP[mode];
    const surface = SURFACE[mode];
    const text = TEXT[mode];
    const currency = opts.currency || "$";

    const cellIndex = {};
    let min = Infinity, max = -Infinity;
    (opts.cells || []).forEach((c) => {
      cellIndex[c.row + "||" + c.col] = c;
      if (typeof c.price === "number") {
        min = Math.min(min, c.price);
        max = Math.max(max, c.price);
      }
    });
    if (!isFinite(min)) { min = 0; max = 1; }

    const wrap = document.createElement("div");
    wrap.className = "d2m-heatmap-wrap";
    wrap.style.setProperty("--d2m-surface", surface);
    wrap.style.setProperty("--d2m-muted", text.muted);
    wrap.style.setProperty("--d2m-navy", "#003087");
    wrap.style.background = surface;
    wrap.style.padding = "16px";
    wrap.style.borderRadius = "8px";
    wrap.style.color = text.primary;

    // legend (always present — sequential magnitude needs a scale key)
    const legend = el("div", { className: "d2m-heatmap-legend" }, [
      el("span", { className: "d2m-legend-label", text: `${currency}${min.toLocaleString()} (cheapest)` }),
      ...ramp.map((hex) => el("span", { className: "d2m-swatch", style: { background: hex } })),
      el("span", { className: "d2m-legend-label", text: `${currency}${max.toLocaleString()} (most expensive)` }),
    ]);
    wrap.appendChild(legend);

    // grid table
    const table = document.createElement("table");
    table.className = "d2m-heatmap-grid";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    const corner = document.createElement("th");
    corner.textContent = opts.rowLabel || "";
    corner.style.color = "#003087";
    headRow.appendChild(corner);
    (opts.cols || []).forEach((c) => {
      const th = document.createElement("th");
      th.textContent = c;
      th.style.color = "#003087";
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tooltip = document.createElement("div");
    tooltip.className = "d2m-heatmap-tooltip";
    document.body.appendChild(tooltip);

    const tbody = document.createElement("tbody");
    (opts.rows || []).forEach((rowKey) => {
      const tr = document.createElement("tr");
      const rowHead = document.createElement("th");
      rowHead.className = "d2m-row-head";
      rowHead.textContent = rowKey;
      rowHead.style.color = "#003087";
      tr.appendChild(rowHead);

      (opts.cols || []).forEach((colKey) => {
        const cell = cellIndex[rowKey + "||" + colKey];
        const td = document.createElement("td");
        td.className = "d2m-cell";
        if (!cell || typeof cell.price !== "number") {
          td.className += " d2m-cell-empty";
          td.textContent = "—";
        } else {
          const step = priceToStep(cell.price, min, max, ramp.length);
          const fill = ramp[step];
          td.style.background = fill;
          td.style.color = contrastText(fill, mode);
          td.textContent = currency + cell.price.toLocaleString();
          td.setAttribute("tabindex", "0");
          td.setAttribute(
            "aria-label",
            `${rowKey}, ${colKey}: ${currency}${cell.price.toLocaleString()}${cell.meta ? ", " + cell.meta : ""}`
          );
          const showTip = (evt) => {
            tooltip.style.display = "block";
            tooltip.textContent = "";
            tooltip.appendChild(el("strong", { text: `${rowKey} · ${colKey}` }));
            tooltip.appendChild(document.createElement("br"));
            tooltip.appendChild(document.createTextNode(`${currency}${cell.price.toLocaleString()}`));
            if (cell.meta) {
              tooltip.appendChild(document.createElement("br"));
              tooltip.appendChild(el("span", { style: { color: "#a8c4f0" }, text: cell.meta }));
            }
            const x = (evt.clientX !== undefined ? evt.clientX : td.getBoundingClientRect().left) + 14;
            const y = (evt.clientY !== undefined ? evt.clientY : td.getBoundingClientRect().top) + 14;
            tooltip.style.left = x + "px";
            tooltip.style.top = y + "px";
          };
          td.addEventListener("mousemove", showTip);
          td.addEventListener("mouseenter", showTip);
          td.addEventListener("focus", showTip);
          td.addEventListener("mouseleave", () => (tooltip.style.display = "none"));
          td.addEventListener("blur", () => (tooltip.style.display = "none"));
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);

    // mandatory table-view fallback (accessibility non-negotiable)
    const details = document.createElement("details");
    details.className = "d2m-heatmap-tableview";
    const summary = document.createElement("summary");
    summary.textContent = "View as table";
    details.appendChild(summary);
    const flat = document.createElement("table");
    flat.appendChild(
      el("thead", null, [
        el("tr", null, [
          el("th", { text: opts.rowLabel || "Row" }),
          el("th", { text: opts.colLabel || "Column" }),
          el("th", { text: "Price" }),
          el("th", { text: "Notes" }),
        ]),
      ])
    );
    const flatBody = document.createElement("tbody");
    (opts.cells || []).forEach((c) => {
      const tr = el("tr", null, [
        el("td", { text: c.row }),
        el("td", { text: c.col }),
        el("td", { text: typeof c.price === "number" ? currency + c.price.toLocaleString() : "—" }),
        el("td", { text: c.meta || "" }),
      ]);
      flatBody.appendChild(tr);
    });
    flat.appendChild(flatBody);
    details.appendChild(flat);
    wrap.appendChild(details);

    container.textContent = "";
    container.appendChild(wrap);
  }

  global.D2MFareHeatmap = { render, RAMP, SURFACE };
})(typeof window !== "undefined" ? window : this);
