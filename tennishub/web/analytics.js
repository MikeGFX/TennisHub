"use strict";

(() => {
  const find = (selector) => document.querySelector(selector);
  const html = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const number = (value) => new Intl.NumberFormat("it-IT", {useGrouping:true}).format(value);
  const date = (value) => new Intl.DateTimeFormat("it-IT", {day:"numeric", month:"short", year:"numeric"}).format(new Date(value + "T12:00:00"));
  const surfaceNames = {all:"Tutte", Hard:"Cemento", Clay:"Terra", Grass:"Erba", Carpet:"Sintetico", Unknown:"Non indicata"};
  let h2hRequest, h2hSurface = "all", submitted = false, historyRequest, historyData, currentReport;
  let chartMode = "year";

  async function json(url, signal) {
    const response = await fetch(url, {signal, cache:"no-store"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Dati non disponibili. Riprova.");
    return data;
  }

  function showView(h2h) {
    find("#h2h-panel").hidden = !h2h;
    find(".season-toolbar > .eyebrow").textContent = h2h ? "CONFRONTA DUE GIOCATORI" : "ESPLORA UNA STAGIONE";
    find(".skip-link").href = h2h ? "#h2h-panel" : "#season-content";
    find(".skip-link").textContent = h2h ? "Vai al testa a testa" : "Vai alla stagione";
    find(".roster-panel").hidden = h2h;
    find(".workspace").classList.toggle("h2h-workspace", h2h);
    find(".season-panel").setAttribute("aria-labelledby", h2h ? "h2h-heading" : "player-name");
    find("#season-content").hidden = h2h;
    find("#season-view").setAttribute("aria-pressed", String(!h2h));
    find("#h2h-view").setAttribute("aria-pressed", String(h2h));
    find("#season-select").closest(".season-tools").classList.toggle("h2h-toolbar", h2h);
    if (h2h) {
      json("/api/bootstrap").then((data) => {
        const selected = find("#h2h-year").value;
        find("#h2h-year").innerHTML = '<option value="all">Tutti gli anni importati</option>' + data.seasons.map((item) => `<option value="${item.year}">${item.year}</option>`).join("");
        if ([...find("#h2h-year").options].some((item) => item.value === selected)) find("#h2h-year").value = selected;
      }).catch(() => {});
    }
  }
  find("#season-view").addEventListener("click", () => showView(false));
  find("#h2h-view").addEventListener("click", () => showView(true));

  for (const side of ["first", "second"]) {
    const input = find(`#h2h-${side}`);
    let request, timer;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      request?.abort();
      const term = input.value.trim();
      find(`#${side}-suggestions`).innerHTML = "";
      if (term.length < 2) return;
      timer = setTimeout(async () => {
        const controller = request = new AbortController();
        try {
          const data = await json(`/api/player-search?q=${encodeURIComponent(term)}`, controller.signal);
          if (controller.signal.aborted) return;
          find(`#${side}-suggestions`).innerHTML = data.players.map((player) => `<option value="${html(player.name)}">${html(player.ioc)} · ${html(player.id)}</option>`).join("");
        } catch (error) { /* Il nome può comunque essere inviato e validato dal server. */ }
      }, 180);
    });
  }

  async function compare() {
    h2hRequest?.abort();
    const controller = h2hRequest = new AbortController();
    submitted = true;
    const host = find("#h2h-results");
    host.setAttribute("aria-busy", "true");
    host.innerHTML = '<p class="analytics-empty">Cerchiamo i confronti nell’archivio…</p>';
    const params = new URLSearchParams({first:find("#h2h-first").value.trim(), second:find("#h2h-second").value.trim(), year:find("#h2h-year").value, surface:h2hSurface, stage:find("#h2h-stage").value});
    try {
      const report = await json(`/api/h2h?${params}`, controller.signal);
      if (controller.signal.aborted) return;
      const summary = report.summary;
      const total = report.by_surface.reduce((sum, row) => sum + row.matches, 0);
      const firstTotal = report.by_surface.reduce((sum, row) => sum + row.first_wins, 0);
      const secondTotal = total - firstTotal;
      const chips = [{surface:"all", matches:total, first_wins:firstTotal, second_wins:secondTotal}, ...report.by_surface.filter((row) => row.surface !== "Unknown" || row.matches)];
      const periods = report.coverage.map((item) => `${item.year} (dati al ${date(item.as_of)})`).join(" · ");
      host.innerHTML = `<div class="h2h-scoreboard"><div><span class="eyebrow">${html(report.first.ioc)}</span><h2>${html(report.first.name)}</h2></div><div class="h2h-score"><strong>${summary.first_wins}</strong><span>–</span><strong>${summary.second_wins}</strong><small>${summary.matches} incontr${summary.matches === 1 ? "o" : "i"} conteggiati</small></div><div><span class="eyebrow">${html(report.second.ioc)}</span><h2>${html(report.second.name)}</h2></div></div>
        <div class="surface-choices" aria-label="Filtra per superficie">${chips.map((row) => `<button type="button" data-h2h-surface="${row.surface}" aria-pressed="${row.surface === h2hSurface}"><span>${surfaceNames[row.surface]}</span><strong>${row.first_wins} – ${row.second_wins}</strong><small>${row.matches} incontri</small></button>`).join("")}</div>
        <p class="analytics-note"><strong>Copertura: ${html(periods)}.</strong> Singolare, inclusi Challenger e qualificazioni se selezionate. È il bilancio dell’archivio disponibile: può differire dall’H2H ufficiale ATP e non copre automaticamente tutta la carriera.</p>
        ${summary.excluded_results ? `<p class="analytics-warning">${summary.excluded_results} risultat${summary.excluded_results === 1 ? "o escluso" : "i esclusi"} dal bilancio: walkover, risultati speciali o punteggio assente. Sono elencati qui sotto.</p>` : ""}
        ${report.matches.length ? `<p class="analytics-note">Punteggi dal punto di vista di ${html(report.first.name)}. Le date sono quelle registrate nella fonte.</p><div class="analytics-table-wrap"><table class="analytics-table"><thead><tr><th>Data</th><th>Torneo / turno</th><th>Superficie</th><th>Vincitore</th><th>Punteggio</th></tr></thead><tbody>${report.matches.map((match) => {
          const won = match.winner_id === report.first.id;
          const score = won ? match.score_winner_first : match.score_winner_first.replace(/(\d+)-(\d+)/g,"$2-$1");
          return `<tr class="${match.counted ? "" : "excluded-match"}"><td>${date(match.date)}</td><td><strong>${html(match.tournament)}</strong><small>${html(match.round || "Turno non indicato")} · ${match.stage === "qualifying" ? "Qualificazioni" : "Tabellone principale"}${match.category === "C" ? " · Challenger" : ""}</small></td><td>${surfaceNames[match.surface]}</td><td>${html(match.winner_name)}${match.counted ? "" : " (escluso)"}</td><td class="score-cell">${html(score || "Non disponibile")}</td></tr>`;
        }).join("")}</tbody></table></div>` : '<p class="analytics-empty">Nessun incontro disponibile con questi filtri. Prova un’altra superficie o stagione.</p>'}`;
    } catch (error) {
      if (!controller.signal.aborted) host.innerHTML = `<p class="analytics-error" role="alert">${html(error.message)}</p><button class="action-button" type="button" data-h2h-retry>Riprova</button>`;
    } finally { if (!controller.signal.aborted) host.setAttribute("aria-busy", "false"); }
  }
  find("#h2h-form").addEventListener("submit", (event) => { event.preventDefault(); compare(); });
  for (const name of ["year", "stage"]) find(`#h2h-${name}`).addEventListener("change", () => { if (submitted) compare(); });
  find("#h2h-results").addEventListener("click", (event) => {
    const button = event.target.closest("[data-h2h-surface]");
    if (button) { h2hSurface = button.dataset.h2hSurface; compare(); }
    if (event.target.closest("[data-h2h-retry]")) compare();
  });

  function chartMarkup(series) {
    const usable = series.filter((item) => item.calculated_events > 0);
    if (!usable.length) return '<p class="analytics-empty">I punti di questa selezione non sono ancora calcolabili. I risultati restano consultabili nella lista dei tornei.</p>';
    const width = 760, height = 275, left = 55, right = 20, top = 20, bottom = 35;
    const maximum = Math.max(100, ...usable.map((item) => item.known_subtotal));
    const maxY = Math.ceil(maximum / 500) * 500;
    const x = (value) => { const [, month, day] = value.split("-").map(Number); return left + (Date.UTC(2000,month-1,day) - Date.UTC(2000,0,1)) / (366*86400000) * (width-left-right); };
    const y = (value) => height - bottom - value / maxY * (height-top-bottom);
    const months = [[0,"GEN"],[3,"APR"],[6,"LUG"],[9,"OTT"],[11,"DIC"]];
    const axis = Array.from({length:5}, (_,index) => { const value=maxY*index/4; return `<line class="chart-grid" x1="${left}" x2="${width-right}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-label" x="${left-10}" y="${y(value)+4}" text-anchor="end">${number(value)}</text>`; }).join("") + months.map(([month,label]) => `<text class="chart-label" x="${x(`2000-${String(month+1).padStart(2,"0")}-01`)}" y="${height-10}" text-anchor="middle">${label}</text>`).join("");
    const curves = usable.map((item,index) => {
      let path = `M ${left} ${y(0)}`;
      const marks = item.timeline.map((event) => {
        const px = x(event.date), py = y(event.cumulative_known_points);
        path += ` H ${px} V ${py}`;
        const title = `${item.year} · ${event.name} · ${date(event.date)}: ${event.earned_points === null ? "punti da verificare" : `${number(event.earned_points)} punti${event.provisional ? " provvisori" : ""}`} · cumulato calcolabile ${number(event.cumulative_known_points)}`;
        return `<circle class="chart-dot series-${index%4}${event.earned_points === null ? " unknown-dot" : ""}" cx="${px}" cy="${py}" r="${event.earned_points === null ? 4 : 3}"><title>${html(title)}</title></circle>`;
      }).join("");
      return `<path class="chart-line series-${index%4}${item.unknown_events ? " partial-line" : ""}" d="${path}"/>${marks}`;
    }).join("");
    return `<svg class="points-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Punti ottenuti cumulati nelle stagioni ${usable.map((item)=>item.year).join(", ")}. Valori completi nella tabella sottostante.">${axis}${curves}</svg>`;
  }

  function renderCharts() {
    const host = find("#points-charts");
    if (!host || !historyData || !currentReport || historyData.player_id !== currentReport.player_id) return;
    const series = chartMode === "compare" ? historyData.seasons : historyData.seasons.filter((item) => item.year === currentReport.season);
    const maximum = Math.max(1,...historyData.seasons.map((item)=>item.known_subtotal));
    host.innerHTML = `<div class="chart-heading"><div><span class="eyebrow">TORNEO DOPO TORNEO</span><h2>Andamento dei punti</h2></div><label><span class="sr-only">Vista del grafico</span><select id="chart-mode"><option value="year">Stagione ${currentReport.season}</option><option value="compare">Confronta le stagioni</option></select></label></div>
      <div class="chart-legend">${series.map((item,index)=>`<span class="series-${index%4}"><i></i>${item.year} · ${item.calculated_events ? number(item.known_subtotal) + (item.unknown_events ? " (subtotale)" : "") : "punti non disponibili"}</span>`).join("")}</div>
      ${chartMarkup(series)}
      <p class="analytics-note">Punti ottenuti nei tornei, non punti della classifica ATP. I valori provvisori sono inclusi. Le date sono quelle degli ultimi incontri registrati nei tornei, non quelle di accredito dei punti.</p>
      ${series.some((item)=>item.unknown_events) ? '<p class="analytics-warning">Le linee tratteggiate mostrano il cumulato dei soli punti calcolabili. I cerchi vuoti segnalano tornei con punti mancanti: non sono zeri.</p>' : ""}
      <details class="chart-data"><summary>Vedi i valori torneo per torneo</summary><div class="analytics-table-wrap"><table class="analytics-table"><thead><tr><th>Anno / data</th><th>Torneo</th><th>Punti ottenuti</th><th>Cumulato calcolabile</th></tr></thead><tbody>${series.flatMap((item)=>item.timeline.map((event)=>`<tr><td>${date(event.date)}</td><td>${html(event.name)}</td><td>${event.earned_points === null ? "Da verificare" : number(event.earned_points)}${event.provisional ? " · provvisori" : ""}</td><td>${number(event.cumulative_known_points)}${event.partial ? " · parziale" : ""}</td></tr>`)).join("")}</tbody></table></div></details>
      <div class="season-totals"><h3>Punti nelle stagioni importate</h3><p class="analytics-note">Confronto dei totali disponibili, senza sommare stagioni diverse. Ogni anno mostra la propria data di aggiornamento.</p>${historyData.seasons.map((item)=>`<div class="season-total-row"><strong>${item.year}</strong>${item.calculated_events ? `<progress value="${item.known_subtotal}" max="${maximum}" aria-label="Punti calcolabili ${item.year}"></progress>` : '<span class="unavailable-bar" aria-hidden="true">—</span>'}<span>${item.calculated_events ? number(item.known_subtotal) : "Non disponibili"}${item.unknown_events && item.calculated_events ? " (parziale)" : ""}</span><small>${item.calculated_events}/${item.events} tornei calcolati · dati al ${date(item.as_of)}${item.unknown_events ? ` · ${item.unknown_events} da verificare` : ""}</small></div>`).join("")}</div>`;
    find("#chart-mode").value = chartMode;
    find("#chart-mode").addEventListener("change", (event) => { chartMode = event.target.value; renderCharts(); });
  }

  async function loadCharts(report) {
    historyRequest?.abort();
    const controller = historyRequest = new AbortController();
    currentReport = report;
    historyData = null;
    chartMode = "year";
    find("#points-charts")?.remove();
    find(".points-note").insertAdjacentHTML("afterend", '<section id="points-charts" class="points-charts" aria-label="Grafici dei punti"><p class="analytics-empty">Prepariamo il grafico dei punti…</p></section>');
    try {
      const data = await json(`/api/points-history?player=${encodeURIComponent(report.player_id)}`,controller.signal);
      if (controller.signal.aborted || report !== currentReport) return;
      historyData = data;
      renderCharts();
    } catch (error) {
      if (!controller.signal.aborted && find("#points-charts")) find("#points-charts").innerHTML = `<p class="analytics-error">${html(error.message)}</p><button type="button" class="action-button" id="retry-chart">Ricarica grafico</button>`;
    }
  }
  window.addEventListener("tennishub:season", (event) => loadCharts(event.detail));
  document.addEventListener("click", (event) => { if(event.target.closest("#retry-chart") && currentReport) loadCharts(currentReport); });
})();
