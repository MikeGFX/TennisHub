// Verifica DOM con HTTP e dati reali. Non verifica il rendering del browser.
// Installazione facoltativa: npm install --prefix .cache/ui-qa --no-save jsdom
// Eseguire con il server avviato: node tests/ui-smoke.cjs [http://127.0.0.1:8765]
const assert = require("node:assert/strict");
const {JSDOM, VirtualConsole} = require("../.cache/ui-qa/node_modules/jsdom");
const base = process.argv[2] || "http://127.0.0.1:8765";
const errors = [];
const pages = [];

async function until(predicate, description) {
  const deadline = Date.now() + 15000;
  while (!predicate()) {
    if (Date.now() > deadline) throw new Error(`Timeout: ${description}`);
    await new Promise((resolve) => setTimeout(resolve, 40));
  }
}

async function main() {
  const html = await (await fetch(base)).text();
  const script = await (await fetch(`${base}/assets/app.js`)).text() + "\n" + await (await fetch(`${base}/assets/analytics.js`)).text();
  async function page(fetchOverride) {
    const console = new VirtualConsole();
    console.on("jsdomError", (error) => errors.push(error));
    const dom = new JSDOM(html, {url: base, runScripts: "outside-only", pretendToBeVisual: true, virtualConsole: console});
    pages.push(dom);
    dom.window.AbortController = AbortController;
    const realFetch = (url, options) => fetch(new URL(url, base), options);
    dom.window.fetch = fetchOverride ? (url, options) => fetchOverride(url, options, realFetch) : realFetch;
    dom.window.addEventListener("error", (event) => errors.push(event.error));
    dom.window.eval(script);
    return dom.window;
  }
  const window = await page();
  const $ = (selector) => window.document.querySelector(selector);
  const all = (selector) => [...window.document.querySelectorAll(selector)];
  const ready = () => $("#season-content").getAttribute("aria-busy") === "false";
  const change = (selector, value) => { $(selector).value = value; $(selector).dispatchEvent(new window.Event("change")); };
  const search = (value) => { $("#player-search").value = value; $("#player-search").dispatchEvent(new window.Event("input")); };
  await until(() => ready() && $("#player-name"), "stagione iniziale");
  assert.equal(all("[data-player-id]").length, 50);
  assert.equal($("#player-name").textContent, "Alexander Zverev");
  assert.equal(all("details.event").length, 22);
  assert.equal(all("details.match").length, 85);
  assert.equal($(".metric-featured .metric-value").textContent, "9.760");
  assert.match($(".metric-featured .metric-caption").textContent, /400 provvisori/);

  await until(() => $(".points-chart"), "grafico annuale");
  assert.equal(all(".season-total-row").length, 2);
  change("#chart-mode", "compare");
  assert.equal(all(".chart-line").length, 2);
  assert.match($(".chart-legend").textContent, /2025/);
  assert.match($(".chart-legend").textContent, /2026/);
  assert.ok($(".historical-points-notice"));
  assert.doesNotMatch($("#points-charts").textContent, /\\u[0-9a-f]{4}/i, "Escape Unicode visibili nei grafici");
  assert.doesNotMatch($("#points-charts").textContent, /[?\uFFFD]/, "Caratteri corrotti nei grafici");
  $(".chart-data summary").click();
  assert.equal($(".chart-data").open, true);
  assert.ok(all(".chart-data tbody tr").length > 22);

  $("#h2h-view").click();
  assert.equal($("#season-content").hidden, true);
  $("#h2h-form").dispatchEvent(new window.Event("submit", {bubbles:true, cancelable:true}));
  await until(() => $(".h2h-scoreboard") && $("#h2h-results").getAttribute("aria-busy") === "false", "H2H");
  const h2h = await (await fetch(`${base}/api/h2h?first=Z355&second=S0AG`)).json();
  assert.equal(all(".h2h-score strong")[0].textContent, String(h2h.summary.first_wins));
  assert.equal(all(".h2h-score strong")[1].textContent, String(h2h.summary.second_wins));
  assert.match($("#h2h-results").textContent, /2025/);
  assert.doesNotMatch($("#h2h-panel").textContent, /[?\uFFFD]/, "Caratteri corrotti nella vista H2H");
  assert.doesNotMatch($("#h2h-panel").textContent, /\\u[0-9a-f]{4}/i, "Escape Unicode visibili nella copertura");
  assert.equal(all(".h2h-coverage li").length, h2h.coverage.length);
  $('[data-h2h-surface="Clay"]').click();
  await until(() => $('[data-h2h-surface="Clay"]')?.getAttribute("aria-pressed") === "true", "filtro superficie H2H");
  const clay = h2h.by_surface.find((item) => item.surface === "Clay");
  assert.equal(all(".h2h-score strong")[0].textContent, String(clay.first_wins));
  assert.equal(all(".h2h-score strong")[1].textContent, String(clay.second_wins));
  await until(() => [...$("#h2h-year").options].some((item)=>item.value === "2025"), "anni H2H");
  change("#h2h-year", "2025");
  await until(() => $(".h2h-scoreboard") && $("#h2h-results").getAttribute("aria-busy") === "false", "filtro anno H2H");
  assert.ok($("#h2h-results .analytics-note").textContent.includes("2025 (dati"));
  assert.ok(!$("#h2h-results .analytics-note").textContent.includes("2026 (dati"));
  $("#h2h-first").value = "Jannik Sinner";
  $("#h2h-form").dispatchEvent(new window.Event("submit", {bubbles:true, cancelable:true}));
  await until(() => $("#h2h-results [role=alert]"), "rifiuto giocatori uguali");
  $("#h2h-first").value = "Alexander Zverev";
  $("#h2h-form").dispatchEvent(new window.Event("submit", {bubbles:true, cancelable:true}));
  await until(() => $(".h2h-scoreboard"), "recupero H2H");
  $("#season-view").click();
  assert.equal($("#season-content").hidden, false);
  change("#chart-mode", "year");

  const report = await (await fetch(`${base}/api/season?year=2026&player=Z355`)).json();
  const lostEvent = report.events.find((event) => event.matches.some((match) => match.loser_id === report.player_id));
  const lossIndex = lostEvent.matches.findIndex((match) => match.loser_id === report.player_id);
  const eventElement = window.document.getElementById(`tournament-${lostEvent.id}`);
  eventElement.querySelector("summary").click();
  assert.equal(eventElement.open, true);
  const matchElement = eventElement.querySelectorAll("details.match")[lossIndex];
  matchElement.querySelector("summary").click();
  assert.equal(matchElement.open, true);
  assert.equal(matchElement.querySelector(".match-score").textContent,
    lostEvent.matches[lossIndex].score_winner_first.replace(/(\d+)-(\d+)/g, "$2-$1"));
  assert.ok(matchElement.querySelector(".stats-table, .no-stats"));

  change("#category-filter", "G");
  assert.equal(all("details.event").length, 4);
  change("#surface-filter", "Grass");
  assert.equal(all("details.event").length, 1);
  change("#category-filter", "250");
  assert.equal(all("details.event").length, 0);
  $('[data-action="reset-filters"]').click();
  assert.equal(all("details.event").length, 22);
  $('[data-category="M"]').click();
  assert.equal(all("details.event").length, report.events.filter((event) => event.category === "M").length);
  $('[data-category="M"]').click();
  assert.equal(all("details.event").length, 22);
  change("#sort-filter", "points");
  const maximum = Math.max(...report.events.map((event) => event.earned_points ?? -1));
  assert.equal(Number($(".event-points").firstChild.textContent.replace(/\D/g, "")), maximum);

  search("sinner");
  assert.equal(all("[data-player-id]").length, 1);
  $("[data-player-id]").click();
  await until(() => ready() && $("#player-name")?.textContent === "Jannik Sinner", "cambio giocatore");
  const sinner = await (await fetch(`${base}/api/season?year=2026&player=S0AG`)).json();
  assert.equal(all("details.event").length, sinner.summary.events);
  if (sinner.summary.events_with_unknown_points) {
    $("#review-filter").click();
    assert.equal(all("details.event").length, sinner.summary.events_with_unknown_points);
    assert.ok(all(".event-points").every((node) => node.textContent.includes("Da verificare")));
  }
  search("nessun-giocatore");
  assert.ok($(".roster-empty"));
  search("");
  assert.equal(all("[data-player-id]").length, 50);
  $('[data-player-id="A0E2"]').click();
  $('[data-player-id="Z355"]').click();
  await until(() => ready() && $("#player-name")?.textContent === "Alexander Zverev", "cambio rapido senza risposte obsolete");
  assert.equal(all("details.event").length, 22);
  assert.equal(new URL(window.location.href).searchParams.get("player"), "Z355");

  let fail = true;
  const retryWindow = await page((url, options, realFetch) => {
    if (fail) { fail = false; return Promise.reject(new Error("Errore di prova")); }
    return realFetch(url, options);
  });
  await until(() => retryWindow.document.querySelector(".error-state"), "stato errore");
  retryWindow.document.querySelector('[data-action="retry"]').click();
  await until(() => retryWindow.document.querySelector(".metric-featured"), "recupero dopo errore");
  const emptyWindow = await page(() => Promise.resolve({ok: true, json: async () => ({seasons: [], needs_import: true})}));
  await until(() => emptyWindow.document.querySelector(".empty-state"), "archivio vuoto");
  assert.equal(emptyWindow.document.querySelector("#season-select").disabled, true);
  assert.deepEqual(errors, []);
  process.stdout.write("UI DOM: ricerca, filtri, dettagli, punteggi, cambio rapido, errori, archivio vuoto, H2H e grafici storici verificati.\n");
}

main().catch((error) => { console.error(error); process.exitCode = 1; }).finally(() => pages.forEach((dom) => dom.window.close()));
