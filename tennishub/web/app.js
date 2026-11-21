"use strict";

const $ = (selector) => document.querySelector(selector);
const formatNumber = (value) => new Intl.NumberFormat("it-IT", {useGrouping: true}).format(value);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
const initials = (name) => name.split(/\s+/).filter(Boolean).filter((word) => word.length > 2).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
const categoryLabels = {G: "Grand Slam", M: "Masters 1000", "500": "ATP 500", "250": "ATP 250", C: "Challenger", F: "ATP Finals", team: "Squadre"};
const countryNames = {GER: "Germania", ITA: "Italia", ESP: "Spagna", USA: "Stati Uniti", FRA: "Francia", AUS: "Australia", GBR: "Gran Bretagna", CAN: "Canada", ARG: "Argentina", BRA: "Brasile", RUS: "Russia", NED: "Paesi Bassi", SRB: "Serbia", CZE: "Cechia", KAZ: "Kazakistan", GRE: "Grecia", NOR: "Norvegia", DEN: "Danimarca", CHI: "Cile", PER: "Perù", BEL: "Belgio", POL: "Polonia", MON: "Monaco", POR: "Portogallo", JPN: "Giappone", CHN: "Cina", CRO: "Croazia", BIH: "Bosnia ed Erzegovina", AUT: "Austria", SUI: "Svizzera", FIN: "Finlandia"};
const surfaces = {Hard: ["Cemento", "hard"], Clay: ["Terra", "clay"], Grass: ["Erba", "grass"], Carpet: ["Sintetico", "carpet"]};
const chevron = '<svg class="chevron" viewBox="0 0 12 12" aria-hidden="true"><path d="m4 2 4 4-4 4"></path></svg>';
const state = {seasons: [], year: null, players: [], playerId: null, report: null, category: "all", surface: "all", sort: "recent", reviewOnly: false, request: null};

function dateText(value, options = {day: "numeric", month: "short", year: "numeric"}) {
  if (!value) return "—";
  const day = new Date(`${value.slice(0, 10)}T12:00:00`);
  return Number.isNaN(day.getTime()) ? "—" : new Intl.DateTimeFormat("it-IT", options).format(day).replaceAll(".", "");
}

function kind(event) { return ["A", "D"].includes(event.category) ? "team" : event.category; }
function categoryName(event) { return event.category_detail || (event.category === "D" ? "Coppa Davis" : categoryLabels[kind(event)]) || event.category; }
function announce(text) { $("#app-status").textContent = text; }
function activePlayer() { return state.players.find((player) => player.id === state.playerId); }
function resetFilters() { state.category = "all"; state.surface = "all"; state.sort = "recent"; state.reviewOnly = false; }

async function getJson(url, signal) {
  const response = await fetch(url, {signal, cache: "no-store"});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Impossibile leggere i dati. Riprova.");
  return result;
}

function beginRequest() {
  state.request?.abort();
  state.request = new AbortController();
  $("#season-content").setAttribute("aria-busy", "true");
  return state.request;
}

function updateLocation(mode = "push") {
  if (mode === "none") return;
  const url = new URL(window.location.href);
  url.searchParams.set("player", state.playerId);
  url.searchParams.set("year", state.year);
  url.hash = "";
  if (mode === "replace") history.replaceState(null, "", url);
  else if (url.href !== window.location.href) history.pushState(null, "", url);
}

function renderRoster() {
  const term = $("#player-search").value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  const filtered = state.players.filter((player) => player.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(term));
  $("#roster-count").textContent = `${filtered.length} giocator${filtered.length === 1 ? "e" : "i"}`;
  $("#player-list").innerHTML = filtered.length ? filtered.map((player) => `
    <button type="button" class="player-option" data-player-id="${escapeHtml(player.id)}" aria-pressed="${player.id === state.playerId}" aria-label="${escapeHtml(player.name)}, posizione ATP ${player.rank}">
      <span class="player-avatar" aria-hidden="true">${escapeHtml(initials(player.name))}</span>
      <span><span class="player-option-name">${escapeHtml(player.name)}</span><span class="player-option-country">${escapeHtml(player.ioc)}</span></span>
      <span class="player-rank">${player.rank}</span>
    </button>`).join("") : '<p class="roster-empty">Nessun giocatore trovato tra i 50 importati. Prova un altro nome.</p>';
}

function updateActivePlayer() {
  document.querySelectorAll("[data-player-id]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.playerId === state.playerId)));
}

function loading() {
  const person = activePlayer();
  $("#season-content").innerHTML = `${person ? playerHeading(person) : ""}<div class="initial-loading"><span class="loading-ball"></span><p>Caricamento della stagione…</p></div>`;
  announce("Caricamento della stagione.");
}

function showError(error) {
  if (error.name === "AbortError") return;
  $("#season-content").setAttribute("aria-busy", "false");
  $("#season-content").innerHTML = `<div class="error-state" role="alert"><h2>Non riusciamo a leggere la stagione</h2><p>${escapeHtml(error.message)}</p><button class="action-button" type="button" data-action="retry">Riprova</button></div>`;
  announce("Errore durante il caricamento.");
}

async function fetchSeason(controller, mode) {
  const report = await getJson(`/api/season?year=${state.year}&player=${encodeURIComponent(state.playerId)}`, controller.signal);
  if (controller.signal.aborted) return;
  state.report = report;
  resetFilters();
  updateLocation(mode);
  renderSeason();
  $("#season-content").setAttribute("aria-busy", "false");
  announce(`${report.player_name}, stagione ${report.season}: ${report.summary.events} partecipazioni disponibili.`);
  window.dispatchEvent(new CustomEvent("tennishub:season", {detail: report}));
}

async function openYear(year, preferredPlayer, mode = "push") {
  const controller = beginRequest();
  state.year = Number(year);
  state.report = null;
  state.players = [];
  state.playerId = null;
  renderRoster();
  $("#season-select").value = state.year;
  loading();
  try {
    const roster = await getJson(`/api/players?year=${state.year}`, controller.signal);
    if (controller.signal.aborted) return;
    state.players = roster.players;
    state.playerId = state.players.some((player) => player.id === preferredPlayer) ? preferredPlayer : (state.players.find((player) => player.id === "Z355") || state.players[0])?.id;
    $("#ranking-date").textContent = `Primi 50 · classifica del ${dateText(roster.ranking_date)}`;
    renderRoster();
    if (!state.playerId) throw new Error("Questa importazione non contiene giocatori in classifica.");
    loading();
    await fetchSeason(controller, mode);
  } catch (error) { if (!controller.signal.aborted) showError(error); }
}

async function openPlayer(playerId, mode = "push") {
  const controller = beginRequest();
  state.playerId = playerId;
  state.report = null;
  updateActivePlayer();
  loading();
  try { await fetchSeason(controller, mode); } catch (error) { if (!controller.signal.aborted) showError(error); }
}

async function reloadArchive() {
  const controller = beginRequest();
  try {
    const data = await getJson("/api/bootstrap", controller.signal);
    if (controller.signal.aborted) return;
    state.seasons = data.seasons;
    if (data.needs_import) {
      state.players = [];
      renderRoster();
      $("#season-select").disabled = true;
      $("#season-content").setAttribute("aria-busy", "false");
      $("#season-content").innerHTML = '<div class="empty-state"><h2>Il tuo archivio parte da qui.</h2><p>Importa una stagione dal terminale del progetto, poi ricarica questa pagina.</p><code>python3 -m tennishub import --season 2026 --as-of 2026-11-18</code><p>Su Windows puoi usare <strong>py -3</strong> al posto di python3.</p><button type="button" class="action-button" data-action="retry">Ricarica archivio</button></div>';
      announce("Nessuna stagione importata.");
      return;
    }
    $("#season-select").innerHTML = state.seasons.map((season) => `<option value="${season.year}">${season.year}</option>`).join("");
    $("#season-select").disabled = false;
    const params = new URLSearchParams(window.location.search);
    const requestedYear = Number(params.get("year") || state.year);
    const year = state.seasons.some((season) => season.year === requestedYear) ? requestedYear : data.default_season;
    await openYear(year, params.get("player") || state.playerId || "Z355", "replace");
  } catch (error) { if (!controller.signal.aborted) showError(error); }
}

function playerHeading(person) {
  return `<div class="player-heading"><div><span class="eyebrow">LA STAGIONE ${state.year}</span><h1 id="player-name">${escapeHtml(person.name)}</h1><p class="player-subtitle">${escapeHtml(countryNames[person.ioc] || person.ioc)} <span aria-hidden="true">·</span> N. ${person.rank} ATP <span aria-hidden="true">·</span> ${formatNumber(person.ranking_points)} punti in classifica</p></div><div class="player-heading-avatar" aria-hidden="true">${escapeHtml(initials(person.name))}</div></div>`;
}

function renderContributions(report) {
  const totals = new Map();
  report.events.forEach((event) => {
    if (event.earned_points > 0) totals.set(kind(event), (totals.get(kind(event)) || 0) + event.earned_points);
  });
  const entries = [...totals.entries()].sort((a, b) => b[1] - a[1]);
  if (!entries.length) return "";
  return `<section class="contributions" aria-labelledby="contribution-heading"><div class="section-label"><h2 id="contribution-heading">Da dove arrivano i punti</h2><p>Distribuzione dei punti calcolabili</p></div><div class="contribution-bar" role="img" aria-label="${escapeHtml(entries.map(([category, points]) => `${categoryLabels[category]}: ${points} punti`).join(", "))}">${entries.map(([category, points]) => `<span class="contribution-segment color-${category}" data-share="${points}"></span>`).join("")}</div><div class="contribution-legend">${entries.map(([category, points]) => `<button type="button" class="legend-item color-${category}" data-category="${category}" aria-pressed="false" aria-label="Mostra tornei ${categoryLabels[category]}"><span class="legend-dot" aria-hidden="true"></span>${categoryLabels[category]}<span class="legend-value">${formatNumber(points)}</span></button>`).join("")}</div></section>`;
}

function renderSeason() {
  const report = state.report;
  const person = activePlayer();
  const summary = report.summary;
  const played = summary.wins + summary.losses;
  const winPercentage = played ? new Intl.NumberFormat("it-IT", {maximumFractionDigits: 1}).format(summary.wins / played * 100) : "—";
  const unknown = summary.events_with_unknown_points;
  const provisional = report.events.filter((event) => event.provisional && event.earned_points !== null).reduce((total, event) => total + event.earned_points, 0);
  const known = summary.events - unknown;
  const totalText = !known && unknown ? "—" : formatNumber(summary.known_earned_points_subtotal);
  const categories = [...new Set(report.events.map(kind))];
  $("#season-content").innerHTML = `${playerHeading(person)}
    ${![2025, 2026].includes(report.season) ? `<div class="year-notice">I risultati del ${report.season} sono disponibili. Il calcolo dei punti per questa stagione è ancora da verificare.</div>` : ""}
    <div class="metric-grid">
      <div class="metric"><span class="metric-label">Tornei disputati</span><strong class="metric-value">${summary.events}</strong><span class="metric-caption">Partecipazioni nella stagione</span></div>
      <div class="metric"><span class="metric-label">Vittorie / sconfitte</span><strong class="metric-value">${summary.wins} <span class="record-losses">/ ${summary.losses}</span></strong><span class="metric-caption">${winPercentage}% di incontri vinti</span></div>
      <div class="metric"><span class="metric-label">Titoli</span><strong class="metric-value">${summary.titles}</strong><span class="metric-caption">Tornei individuali vinti</span></div>
      <div class="metric metric-featured"><span class="metric-label">${unknown ? "Subtotale punti ottenuti" : "Punti ottenuti"}</span><strong class="metric-value">${totalText}</strong><span class="metric-caption">${unknown ? `${unknown} torne${unknown === 1 ? "o da verificare" : "i da verificare"}` : provisional ? `${formatNumber(provisional)} provvisori inclusi` : "Calcolati per ogni torneo"}</span></div>
    </div>
    <p class="points-note"><span class="note-icon" aria-hidden="true">i</span><span>Punti ottenuti nei tornei, compresi quelli in corso. Il totale può differire dai punti della classifica ATP.${unknown ? " I valori da verificare sono esclusi dal subtotale." : ""}</span></p>
    ${renderContributions(report)}
    <section aria-labelledby="tournaments-heading"><div class="tournament-heading"><h2 id="tournaments-heading">Il percorso della stagione <span id="event-count" class="count-label"></span></h2><span class="data-date">Dati al ${dateText(report.as_of)}</span></div>
    <div class="filters">
      <label class="sr-only" for="category-filter">Categoria del torneo</label><select id="category-filter" class="filter-select"><option value="all">Tutte le categorie</option>${["G", "M", "500", "250", "C", "F", "team"].filter((category) => categories.includes(category)).map((category) => `<option value="${category}">${categoryLabels[category]}</option>`).join("")}</select>
      <label class="sr-only" for="surface-filter">Superficie</label><select id="surface-filter" class="filter-select"><option value="all">Tutte le superfici</option>${Object.entries(surfaces).filter(([surface]) => report.events.some((event) => event.surface === surface)).map(([surface, [label]]) => `<option value="${surface}">${label}</option>`).join("")}</select>
      ${unknown ? `<button type="button" id="review-filter" class="review-filter" aria-pressed="false">Da verificare · ${unknown}</button>` : ""}
      <label class="sr-only" for="sort-filter">Ordine dei tornei</label><select id="sort-filter" class="filter-select"><option value="recent">Più recenti</option><option value="oldest">Prima i più lontani</option><option value="points">Più punti</option></select>
    </div><div id="events"></div></section>`;
  document.querySelectorAll("[data-share]").forEach((segment) => { segment.style.flexGrow = Number(segment.dataset.share); });
  $("#category-filter").addEventListener("change", (event) => { state.category = event.target.value; renderEvents(); });
  $("#surface-filter").addEventListener("change", (event) => { state.surface = event.target.value; renderEvents(); });
  $("#sort-filter").addEventListener("change", (event) => { state.sort = event.target.value; renderEvents(); });
  $("#review-filter")?.addEventListener("click", () => { state.reviewOnly = !state.reviewOnly; renderEvents(); });
  renderEvents();
}

function safeLink(url) {
  try { const parsed = new URL(url); return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : null; } catch { return null; }
}

function renderEvent(event) {
  const surface = surfaces[event.surface] || ["Non indicata", "unknown"];
  const day = dateText(event.first_recorded_date, {day: "2-digit"});
  const month = dateText(event.first_recorded_date, {month: "short"}).toUpperCase();
  const champion = event.placement === "Vincitore";
  const placement = event.placement.replace("In corso: RR", "Gironi · in corso").replace("Singolare a squadre:", "Singolare:");
  const pointDisplay = event.earned_points === null ? '<span class="review-tag">Da verificare</span>' : `${formatNumber(event.earned_points)}${event.provisional ? '<span class="point-note provisional-label">Provvisori</span>' : '<span class="point-note">punti</span>'}`;
  const sources = [...new Set(event.points_sources || [])].map(safeLink).filter(Boolean);
  const links = sources.map((url, index) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${index ? "Livello dell’edizione" : "Regole dei punti"} ↗</a>`).join("");
  const breakdown = event.points_breakdown;
  const breakdownText = breakdown && breakdown.qualifying > 0 && breakdown.main_draw !== null ? `Tabellone principale: ${formatNumber(breakdown.main_draw)} · Qualificazioni: ${formatNumber(breakdown.qualifying)}.` : "";
  return `<details class="event" id="tournament-${escapeHtml(event.id)}"><summary class="event-summary" aria-label="${escapeHtml(event.name)}, ${escapeHtml(placement)}, ${event.earned_points === null ? "punti da verificare" : `${event.earned_points} punti`}. Apri gli incontri">
    <span class="event-date" title="Prima data registrata per gli incontri del giocatore"><strong>${day}</strong>${month}</span>
    <span><span class="event-name">${escapeHtml(event.name)}</span><span class="event-category">${escapeHtml(categoryName(event))}</span></span>
    <span class="surface surface-${surface[1]}"><span class="surface-dot" aria-hidden="true"></span>${surface[0]}</span>
    <span class="placement${champion ? " champion" : ""}">${champion ? '<span class="trophy" aria-hidden="true">★</span>' : ""}${escapeHtml(placement)}</span>
    <span class="event-points">${pointDisplay}</span>${chevron}
    </summary><div class="event-content"><div class="event-detail-top"><div class="points-explanation"><p>${escapeHtml(event.points_reason)}</p>${breakdownText ? `<p>${breakdownText}</p>` : ""}<div class="rule-links">${links}</div></div><div class="detail-record">${event.wins} vittorie / ${event.losses} sconfitte</div></div>
    <p class="match-legend">Punteggi dal punto di vista di ${escapeHtml(state.report.player_name)}. Apri un incontro per le statistiche.</p><div class="match-list">${event.matches.map(renderMatch).join("")}</div></div></details>`;
}

function renderEvents() {
  if (!state.report) return;
  let events = state.report.events.filter((event) => (state.category === "all" || kind(event) === state.category) && (state.surface === "all" || event.surface === state.surface) && (!state.reviewOnly || event.earned_points === null));
  events = [...events].sort((a, b) => state.sort === "points" ? (b.earned_points ?? -1) - (a.earned_points ?? -1) || b.first_recorded_date.localeCompare(a.first_recorded_date) : state.sort === "oldest" ? a.first_recorded_date.localeCompare(b.first_recorded_date) : b.first_recorded_date.localeCompare(a.first_recorded_date));
  $("#event-count").textContent = `${events.length} torne${events.length === 1 ? "o" : "i"}`;
  $("#category-filter").value = state.category;
  $("#surface-filter").value = state.surface;
  $("#sort-filter").value = state.sort;
  $("#review-filter")?.setAttribute("aria-pressed", String(state.reviewOnly));
  document.querySelectorAll("[data-category]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.category === state.category)));
  $("#events").innerHTML = events.length ? `<div class="event-table"><div class="event-table-heading" aria-hidden="true"><span>Primo<br>incontro</span><span>Torneo</span><span class="surface-heading">Superficie</span><span>Piazzamento</span><span class="points-heading">Punti ottenuti</span><span></span></div>${events.map(renderEvent).join("")}</div>` : `<div class="empty-filter">${state.report.events.length ? "Nessun torneo corrisponde ai filtri selezionati." : "Nessun incontro disponibile per questo giocatore nella stagione."}${state.report.events.length ? '<button type="button" data-action="reset-filters">Mostra tutti i tornei</button>' : ""}</div>`;
}

function numeric(raw, key) {
  const value = raw[key];
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function percent(raw, numerator, denominator) {
  const n = numeric(raw, numerator), d = numeric(raw, denominator);
  return n === null || d === null || d === 0 ? "—" : `${Math.round(n / d * 100)}%`;
}

function renderMatch(match) {
  const raw = match.raw;
  const won = match.winner_id === state.report.player_id;
  const opponent = won ? raw.loser_name : raw.winner_name;
  const unplayed = /W\/O|DEF|ABN|BYE/i.test(match.score_winner_first);
  const score = won ? match.score_winner_first : match.score_winner_first.replace(/(\d+)-(\d+)/g, "$2-$1");
  const own = won ? "w_" : "l_", other = won ? "l_" : "w_";
  const statistics = [
    ["Ace", numeric(raw, `${own}ace`), numeric(raw, `${other}ace`)],
    ["Doppi falli", numeric(raw, `${own}df`), numeric(raw, `${other}df`)],
    ["Prime in campo", percent(raw, `${own}1stIn`, `${own}svpt`), percent(raw, `${other}1stIn`, `${other}svpt`)],
    ["Punti vinti sulla prima", percent(raw, `${own}1stWon`, `${own}1stIn`), percent(raw, `${other}1stWon`, `${other}1stIn`)],
    ["Punti vinti sulla seconda", secondServe(raw, own), secondServe(raw, other)],
    ["Palle break salvate", fraction(raw, `${own}bpSaved`, `${own}bpFaced`), fraction(raw, `${other}bpSaved`, `${other}bpFaced`)],
  ];
  const hasStats = ["w_ace", "l_ace", "w_svpt", "l_svpt", "w_df", "l_df"].some((key) => numeric(raw, key) !== null);
  const round = match.stage === "qualifying" ? `Q${match.round.replace(/^Q/, "")}` : ({F: "Finale", SF: "SF", QF: "QF", RR: "Gironi"}[match.round] || match.round || "—");
  return `<details class="match"><summary class="match-summary"><span class="match-round">${escapeHtml(round)}</span><span class="match-opponent">${escapeHtml(opponent)}</span><span class="match-result ${unplayed ? "unplayed" : won ? "" : "loss"}">${unplayed ? "W/O" : won ? "V" : "S"}<span class="sr-only">${unplayed ? "Incontro non disputato" : won ? "Vittoria" : "Sconfitta"}</span></span><span class="match-score">${escapeHtml(score)}</span>${chevron}</summary><div class="match-info"><p class="match-meta">${dateText(match.date)}${numeric(raw, "minutes") !== null ? ` · ${formatNumber(numeric(raw, "minutes"))} minuti` : ""}${unplayed ? " · Incontro non conteggiato nel record dei match giocati" : ""}</p>${hasStats ? `<table class="stats-table"><thead><tr><th scope="col">Statistiche</th><th scope="col">${escapeHtml(state.report.player_name.split(" ").slice(-1)[0])}</th><th scope="col">${escapeHtml(opponent.split(" ").slice(-1)[0])}</th></tr></thead><tbody>${statistics.map(([label, first, second]) => `<tr><td>${label}</td><td>${first ?? "—"}</td><td>${second ?? "—"}</td></tr>`).join("")}</tbody></table>` : '<p class="no-stats">Le statistiche di questo incontro non sono disponibili nella fonte.</p>'}<p class="match-footnote">La data è quella registrata nella fonte.</p></div></details>`;
}

function fraction(raw, first, second) {
  const a = numeric(raw, first), b = numeric(raw, second);
  return a === null || b === null ? "—" : `${a} / ${b}`;
}

function secondServe(raw, side) {
  const points = numeric(raw, `${side}svpt`), firstIn = numeric(raw, `${side}1stIn`), won = numeric(raw, `${side}2ndWon`);
  return points === null || firstIn === null || won === null || points <= firstIn ? "—" : `${Math.round(won / (points - firstIn) * 100)}%`;
}

$("#player-search").addEventListener("input", renderRoster);
$("#player-list").addEventListener("click", (event) => { const button = event.target.closest("[data-player-id]"); if (button && button.dataset.playerId !== state.playerId) openPlayer(button.dataset.playerId); });
$("#season-select").addEventListener("change", (event) => openYear(Number(event.target.value), state.playerId));
$("#reload").addEventListener("click", reloadArchive);
$("#season-content").addEventListener("click", (event) => {
  const category = event.target.closest("[data-category]");
  if (category) { state.category = state.category === category.dataset.category ? "all" : category.dataset.category; renderEvents(); return; }
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "retry") reloadArchive();
  if (action === "reset-filters") { resetFilters(); renderEvents(); }
});
window.addEventListener("popstate", () => {
  const params = new URLSearchParams(window.location.search);
  const year = Number(params.get("year"));
  if (state.seasons.some((season) => season.year === year)) openYear(year, params.get("player"), "none");
});
reloadArchive();
