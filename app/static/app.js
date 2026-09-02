(function () {
  "use strict";

  const state = {
    instruments: [],
    instrumentsByTicker: {},
  };

  const holdingsBody = document.getElementById("holdings-body");
  const addRowBtn = document.getElementById("add-row-btn");
  const weightSumEl = document.getElementById("weight-sum");
  const validateBtn = document.getElementById("validate-btn");
  const errorBanner = document.getElementById("error-banner");
  const resultCard = document.getElementById("result-card");
  const statusBar = document.getElementById("status-bar");
  const violationsList = document.getElementById("violations-list");
  const violationsEmpty = document.getElementById("violations-empty");
  const warningsList = document.getElementById("warnings-list");
  const warningsEmpty = document.getElementById("warnings-empty");
  const exposuresStats = document.getElementById("exposures-stats");
  const exposureAssetClass = document.getElementById("exposure-asset-class");
  const exposureSector = document.getElementById("exposure-sector");
  const exposureGeography = document.getElementById("exposure-geography");
  const nearestSection = document.getElementById("nearest-section");
  const nearestBody = document.getElementById("nearest-body");
  const nearestExplanation = document.getElementById("nearest-explanation");

  let rowCounter = 0;

  function formatPct(value, decimals) {
    const d = decimals === undefined ? 1 : decimals;
    return Number(value).toLocaleString("nb-NO", {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  }

  function formatSignedPct(value, decimals) {
    const formatted = formatPct(Math.abs(value), decimals);
    if (value > 0) return "+" + formatted;
    if (value < 0) return "−" + formatted;
    return formatted;
  }

  function formatCount(value) {
    return Number(value).toLocaleString("nb-NO", { maximumFractionDigits: 0 });
  }

  // --- Instrumentliste ---

  async function loadInstruments() {
    const response = await fetch("/instruments");
    if (!response.ok) {
      throw new Error("Klarte ikke å hente instrumenter fra serveren.");
    }
    state.instruments = await response.json();
    state.instruments.sort((a, b) => a.ticker.localeCompare(b.ticker));
    state.instrumentsByTicker = {};
    state.instruments.forEach((inst) => {
      state.instrumentsByTicker[inst.ticker] = inst;
    });
  }

  function buildInstrumentOptionsHtml() {
    let html = '<option value="">Velg instrument…</option>';
    state.instruments.forEach((inst) => {
      html += `<option value="${inst.ticker}">${inst.ticker} — ${inst.name}</option>`;
    });
    return html;
  }

  // --- Rader ---

  function addRow() {
    rowCounter += 1;
    const tr = document.createElement("tr");
    tr.dataset.rowId = String(rowCounter);
    tr.innerHTML = `
      <td><select class="ticker-select">${buildInstrumentOptionsHtml()}</select></td>
      <td><input type="number" class="weight-input" min="0" max="100" step="0.01" placeholder="0"></td>
      <td><button type="button" class="remove-row-btn" aria-label="Fjern rad">✕</button></td>
    `;
    holdingsBody.appendChild(tr);
  }

  function removeRow(tr) {
    tr.remove();
    updateWeightSum();
  }

  function collectHoldings() {
    const holdings = [];
    holdingsBody.querySelectorAll("tr").forEach((tr) => {
      const ticker = tr.querySelector(".ticker-select").value;
      const weightRaw = tr.querySelector(".weight-input").value;
      if (!ticker || weightRaw === "") return;
      const weight = parseFloat(weightRaw);
      if (Number.isNaN(weight)) return;
      holdings.push({ ticker: ticker, weight_pct: weight });
    });
    return holdings;
  }

  function updateWeightSum() {
    const holdings = collectHoldings();
    const sum = holdings.reduce((acc, h) => acc + h.weight_pct, 0);
    weightSumEl.textContent = "Sum: " + formatPct(sum) + " %";
    weightSumEl.classList.remove("sum-ok", "sum-off");
    if (Math.abs(sum - 100) < 0.005) {
      weightSumEl.classList.add("sum-ok");
    } else if (holdings.length > 0) {
      weightSumEl.classList.add("sum-off");
    }
  }

  holdingsBody.addEventListener("input", updateWeightSum);
  holdingsBody.addEventListener("change", updateWeightSum);
  holdingsBody.addEventListener("click", (event) => {
    const btn = event.target.closest(".remove-row-btn");
    if (btn) {
      removeRow(btn.closest("tr"));
    }
  });
  addRowBtn.addEventListener("click", addRow);

  // --- Feilmeldinger ---

  function showError(message) {
    errorBanner.textContent = message;
    errorBanner.hidden = false;
  }

  function hideError() {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
  }

  function formatApiError(data) {
    const detail = data && data.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          const loc = Array.isArray(item.loc)
            ? item.loc.filter((p) => p !== "body").join(" → ")
            : "";
          return loc ? `${loc}: ${item.msg}` : item.msg;
        })
        .join(" | ");
    }
    return "Ukjent feil fra serveren.";
  }

  // --- Validering ---

  async function handleValidate() {
    hideError();
    const holdings = collectHoldings();
    if (holdings.length === 0) {
      showError("Legg til minst én posisjon med instrument og vekt.");
      return;
    }

    validateBtn.disabled = true;
    validateBtn.textContent = "Validerer…";

    try {
      const response = await fetch("/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ holdings: holdings }),
      });
      const data = await response.json();

      if (!response.ok) {
        showError(formatApiError(data));
        resultCard.hidden = true;
        return;
      }

      renderResult(data, holdings);
    } catch (err) {
      showError("Klarte ikke å nå serveren. Prøv igjen.");
      resultCard.hidden = true;
    } finally {
      validateBtn.disabled = false;
      validateBtn.textContent = "Valider portefølje";
    }
  }

  validateBtn.addEventListener("click", handleValidate);

  // --- Resultatvisning ---

  function formatFinding(finding) {
    // Backend returnerer unit ("percent" eller "count") per regelbrudd, avledet i
    // app/domain/rules.py der metric_definition uansett allerede avgjør hvilken Exposures-verdi
    // som brukes. Å gjenta den samme "count"-i-metric_definition-sjekken her ville dupliserte
    // domenelogikk i frontend og brutt med at rules.csv (via backend) er kilden til sannhet.
    const isCount = finding.unit === "count";
    const format = isCount ? formatCount : formatPct;
    const suffix = isCount ? "" : " %";
    const actual = format(finding.actual_value);
    const threshold = format(finding.threshold);
    let comparison;
    if (finding.operator === "<=") {
      comparison = `målt ${actual}${suffix}, maks ${threshold}${suffix}`;
    } else if (finding.operator === ">=") {
      comparison = `målt ${actual}${suffix}, minst ${threshold}${suffix}`;
    } else {
      comparison = `målt ${actual}${suffix}, skal være ${threshold}${suffix}`;
    }
    const scopeIsGroup = !["portfolio", "holding"].includes(finding.scope_detail);
    const scope = scopeIsGroup ? ` – ${finding.scope_detail}` : "";
    let excess = "";
    if (finding.excess > 0.005) {
      const excessUnit = isCount ? (Math.round(finding.excess) === 1 ? " posisjon" : " posisjoner") : " pp";
      excess = ` (avvik ${format(finding.excess)}${excessUnit})`;
    }
    return { title: finding.rule_code, text: `${finding.description}${scope}: ${comparison}${excess}` };
  }

  function renderFindingList(listEl, emptyEl, findings, severityClass) {
    listEl.innerHTML = "";
    if (findings.length === 0) {
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    findings.forEach((finding) => {
      const { title, text } = formatFinding(finding);
      const li = document.createElement("li");
      li.className = "finding-item " + severityClass;
      li.innerHTML = `<span class="rule-code">${title}</span>${text}`;
      listEl.appendChild(li);
    });
  }

  function renderExposureList(listEl, groupMap) {
    listEl.innerHTML = "";
    const entries = Object.entries(groupMap).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) {
      listEl.innerHTML = '<li><span class="group-name">Ingen</span></li>';
      return;
    }
    entries.forEach(([name, value]) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="group-name">${name}</span><span class="group-value">${formatPct(value)} %</span>`;
      listEl.appendChild(li);
    });
  }

  const CATEGORY_LABELS = {
    added: "Lagt til",
    removed: "Fjernet",
    adjusted: "Justert",
    unchanged: "Uendret",
  };

  function renderNearestTable(nearestHoldings, changeSummary, submittedHoldings) {
    const originalByTicker = {};
    submittedHoldings.forEach((h) => {
      originalByTicker[h.ticker] = (originalByTicker[h.ticker] || 0) + h.weight_pct;
    });
    const newByTicker = {};
    nearestHoldings.forEach((h) => {
      newByTicker[h.ticker] = h.weight_pct;
    });
    const changeByTicker = {};
    changeSummary.forEach((c) => {
      changeByTicker[c.ticker] = c;
    });

    const tickers = Array.from(
      new Set([...Object.keys(originalByTicker), ...Object.keys(newByTicker)])
    ).sort();

    nearestBody.innerHTML = "";
    tickers.forEach((ticker) => {
      const original = originalByTicker[ticker] || 0;
      const now = newByTicker[ticker] || 0;
      const change = changeByTicker[ticker];
      const category = change ? change.category : "unchanged";
      const diff = change ? change.diff_pct : 0;
      const explanation = change ? change.explanation : "";
      const instrument = state.instrumentsByTicker[ticker];
      const name = instrument ? instrument.name : "";

      const tr = document.createElement("tr");
      if (category === "unchanged") tr.className = "row-unchanged";
      tr.innerHTML = `
        <td><strong>${ticker}</strong><br><span class="group-name">${name}</span></td>
        <td>${formatPct(original)} %</td>
        <td>${formatPct(now)} %</td>
        <td>${formatSignedPct(diff)} pp</td>
        <td><span class="status-badge ${category}">${CATEGORY_LABELS[category] || category}</span></td>
        <td>${explanation}</td>
      `;
      nearestBody.appendChild(tr);
    });
  }

  function renderResult(data, submittedHoldings) {
    resultCard.hidden = false;

    statusBar.textContent = data.summary;
    statusBar.className = "status-bar " + (data.portfolio_valid ? "valid" : "invalid");

    renderFindingList(violationsList, violationsEmpty, data.violations, "error");
    renderFindingList(warningsList, warningsEmpty, data.warnings, "warning");

    const exposures = data.exposures;
    exposuresStats.textContent =
      `${exposures.number_of_holdings} posisjoner · ` +
      `sum ${formatPct(exposures.total_weight)} % · ` +
      `største posisjon ${formatPct(exposures.max_holding_weight)} % · ` +
      `${exposures.unknown_classification_count} med ukjent klassifisering`;
    renderExposureList(exposureAssetClass, exposures.by_asset_class);
    renderExposureList(exposureSector, exposures.by_sector);
    renderExposureList(exposureGeography, exposures.by_geography);

    if (data.nearest_valid_portfolio) {
      nearestSection.hidden = false;
      nearestExplanation.hidden = true;
      renderNearestTable(data.nearest_valid_portfolio, data.change_summary || [], submittedHoldings);
    } else {
      nearestSection.hidden = true;
      if (!data.portfolio_valid && data.nearest_valid_explanation) {
        nearestExplanation.hidden = false;
        nearestExplanation.textContent = data.nearest_valid_explanation;
      } else {
        nearestExplanation.hidden = true;
      }
    }
  }

  // --- Oppstart ---

  async function init() {
    addRow();
    addRow();
    addRow();
    updateWeightSum();
    try {
      await loadInstruments();
      holdingsBody.querySelectorAll(".ticker-select").forEach((select) => {
        select.innerHTML = buildInstrumentOptionsHtml();
      });
    } catch (err) {
      showError(err.message || "Klarte ikke å hente instrumenter.");
    }
  }

  init();
})();
