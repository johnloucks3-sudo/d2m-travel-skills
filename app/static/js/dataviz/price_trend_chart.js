/**
 * D2M 30-Day Price Trend Line
 * Component 3 of docs/DATAVIZ_FLIGHT_CHARTS_SPEC_20260710.md
 *
 * Form: single-route fare history over time, polarity vs a baseline price.
 * Color: DIVERGING — gold (#d4af37, price up vs baseline) <- gray (#95a5a6,
 * baseline/flat, +/-1%) -> navy (#003087, price down vs baseline). Per the
 * dataviz skill's color-formula.md, a diverging palette is NOT run through
 * the categorical validator (it will fail by design — the checks are for
 * 8-hue identity sets). It is verified instead for lightness monotonicity
 * per arm from the neutral midpoint outward; see the spec doc for the
 * OKLCH values and the manual verification.
 *
 * Requires Chart.js (already CDN-loaded by every existing flight-option
 * artifact in this repo — see output/loucks_silvernova_2027_flight_options.html).
 * One axis only (price, $ per person). No dual-axis.
 *
 * Usage:
 *   D2MPriceTrend.render(canvasEl, tableContainerEl, {
 *     points: [ { date: "2026-07-01", price_pp: 5200 }, ... ],  // sorted asc
 *     baseline_price_pp: 5024,
 *     label: "DEN → VCE · Business",
 *     currency: "$",
 *   });
 */
(function (global) {
  "use strict";

  const GOLD = "#d4af37";
  const GRAY = "#95a5a6";
  const NAVY = "#003087";
  const FLAT_BAND_PCT = 1.0; // within +/-1% of baseline reads as "flat" (gray)

  function classify(price, baseline) {
    if (!baseline) return "flat";
    const pct = ((price - baseline) / baseline) * 100;
    if (pct > FLAT_BAND_PCT) return "up";
    if (pct < -FLAT_BAND_PCT) return "down";
    return "flat";
  }

  function colorFor(cls) {
    return cls === "up" ? GOLD : cls === "down" ? NAVY : GRAY;
  }

  function pctChange(price, baseline) {
    if (!baseline) return 0;
    return ((price - baseline) / baseline) * 100;
  }

  function el(tag, props, children) {
    const node = document.createElement(tag);
    if (props) {
      Object.keys(props).forEach((k) => {
        if (k === "text") node.textContent = props[k];
        else if (k === "style") Object.assign(node.style, props[k]);
        else node[k] = props[k];
      });
    }
    (children || []).forEach((c) => node.appendChild(c));
    return node;
  }

  function renderLegendAndTable(container, opts, points) {
    container.textContent = "";
    const wrap = el("div", { style: { fontFamily: "Georgia, serif", fontSize: "12px" } });

    const legend = el("div", {
      style: { display: "flex", gap: "16px", alignItems: "center", margin: "8px 0", fontSize: "11px" },
    }, [
      el("span", null, [
        el("span", { style: { display: "inline-block", width: "12px", height: "12px", background: GOLD, borderRadius: "50%", marginRight: "4px", verticalAlign: "middle" } }),
        el("span", { text: `Above baseline (>+${FLAT_BAND_PCT}%)` }),
      ]),
      el("span", null, [
        el("span", { style: { display: "inline-block", width: "12px", height: "12px", background: GRAY, borderRadius: "50%", marginRight: "4px", verticalAlign: "middle" } }),
        el("span", { text: `Baseline (±${FLAT_BAND_PCT}%)` }),
      ]),
      el("span", null, [
        el("span", { style: { display: "inline-block", width: "12px", height: "12px", background: NAVY, borderRadius: "50%", marginRight: "4px", verticalAlign: "middle" } }),
        el("span", { text: `Below baseline (<-${FLAT_BAND_PCT}%)` }),
      ]),
    ]);
    wrap.appendChild(legend);

    const details = el("details", { style: { marginTop: "8px" } });
    details.appendChild(el("summary", { text: "View as table", style: { cursor: "pointer", color: NAVY, fontWeight: "bold" } }));
    const table = el("table", { style: { borderCollapse: "collapse", width: "100%", marginTop: "6px" } });
    table.appendChild(
      el("thead", null, [
        el("tr", null, [
          el("th", { text: "Date", style: { textAlign: "left", borderBottom: "1px solid #ddd", padding: "4px 8px" } }),
          el("th", { text: "Price/pp", style: { textAlign: "right", borderBottom: "1px solid #ddd", padding: "4px 8px" } }),
          el("th", { text: "vs baseline", style: { textAlign: "right", borderBottom: "1px solid #ddd", padding: "4px 8px" } }),
        ]),
      ])
    );
    const tbody = el("tbody");
    points.forEach((p) => {
      const cls = classify(p.price_pp, opts.baseline_price_pp);
      const pct = pctChange(p.price_pp, opts.baseline_price_pp);
      tbody.appendChild(
        el("tr", null, [
          el("td", { text: p.date, style: { padding: "4px 8px", borderBottom: "1px solid #f0f0f0" } }),
          el("td", { text: `${opts.currency || "$"}${p.price_pp.toLocaleString()}`, style: { padding: "4px 8px", textAlign: "right", borderBottom: "1px solid #f0f0f0" } }),
          el("td", { text: `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`, style: { padding: "4px 8px", textAlign: "right", borderBottom: "1px solid #f0f0f0", color: colorFor(cls), fontWeight: "bold" } }),
        ])
      );
    });
    table.appendChild(tbody);
    details.appendChild(table);
    wrap.appendChild(details);
    container.appendChild(wrap);
  }

  function render(canvasEl, tableContainerEl, opts) {
    const points = (opts.points || []).slice().sort((a, b) => a.date.localeCompare(b.date));
    const baseline = opts.baseline_price_pp;
    const currency = opts.currency || "$";

    if (tableContainerEl) renderLegendAndTable(tableContainerEl, opts, points);

    if (typeof Chart === "undefined") {
      console.warn("D2MPriceTrend: Chart.js not loaded — skipping canvas render, table view still available");
      return null;
    }

    const labels = points.map((p) => p.date);
    const data = points.map((p) => p.price_pp);
    const pointColors = points.map((p) => colorFor(classify(p.price_pp, baseline)));

    // First/last always direct-labeled (diverging marks carry a sub-3:1
    // contrast WARN on some steps — direct labels are the mandated relief).
    const pointRadii = points.map((_, i) => (i === 0 || i === points.length - 1 ? 6 : 3));

    const chart = new Chart(canvasEl.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: opts.label || "Fare trend",
            data,
            borderColor: GRAY,
            segment: {
              borderColor: (ctx) => {
                const v = ctx.p1.parsed.y;
                return colorFor(classify(v, baseline));
              },
            },
            backgroundColor: "rgba(149,165,166,0.08)",
            pointBackgroundColor: pointColors,
            pointBorderColor: "#ffffff",
            pointRadius: pointRadii,
            pointHoverRadius: 8,
            borderWidth: 2,
            tension: 0.15,
            fill: true,
          },
          baseline
            ? {
                label: "Baseline",
                data: points.map(() => baseline),
                borderColor: GRAY,
                borderDash: [4, 4],
                pointRadius: 0,
                borderWidth: 1,
                fill: false,
              }
            : null,
        ].filter(Boolean),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false }, // crosshair-style hover
        plugins: {
          legend: { display: true, position: "bottom" },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                if (ctx.dataset.label === "Baseline") return `Baseline: ${currency}${baseline.toLocaleString()}`;
                const v = ctx.parsed.y;
                const pct = pctChange(v, baseline);
                return `${currency}${v.toLocaleString()}/pp (${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% vs baseline)`;
              },
            },
          },
        },
        scales: {
          y: {
            title: { display: true, text: `Price per person (${currency})` },
            ticks: { callback: (v) => currency + v.toLocaleString() },
          },
          x: { title: { display: true, text: "Date" } },
        },
      },
    });

    // Defensive resize: on a tall page (route map + heatmap cards above this
    // chart), Chart.js can measure the canvas before the browser has
    // committed layout for everything above it, producing a 0-size internal
    // chart area with no thrown error — axes and legend still draw (they use
    // fixed metrics) but the dataset itself never paints. Forcing a resize
    // one frame later — after layout has settled — fixes it reliably.
    // Reproduced and confirmed via scripts/flight_route_visuals_refresh.py's
    // demo artifact (SVG route maps + heatmap above the canvas); this is
    // NOT a bug in the diverging-color logic, purely a layout-timing race.
    requestAnimationFrame(() => chart.resize());
    if (document.readyState !== "complete") {
      window.addEventListener("load", () => chart.resize(), { once: true });
    }

    return chart;
  }

  global.D2MPriceTrend = { render, classify, colorFor, pctChange, GOLD, GRAY, NAVY };
})(typeof window !== "undefined" ? window : this);
