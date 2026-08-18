// ---------- utilitaires ----------
const $ = s => document.querySelector(s);
const color = s => s >= 8 ? 'var(--good)' : s >= 5 ? 'var(--ok)' : 'var(--bad)';
const fcolor = f => f >= 0.8 ? 'var(--good)' : f >= 0.55 ? 'var(--ok)' : 'var(--bad)';
const arrow = d => `<span style="display:inline-block;transform:rotate(${d}deg)">↓</span> ${Math.round(d)}°`;
const md = t => t.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

let SPOTS = {};
const spotSel = $('#spot'), modelSel = $('#model');

// ---------- onglets ----------
document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  $('#' + t.dataset.tab).classList.add('active');
  if (t.dataset.tab === 'science') renderScience();
});

// ---------- init ----------
(async () => {
  SPOTS = await (await fetch('/api/spots')).json();
  Object.entries(SPOTS).forEach(([k, v]) => {
    const o = document.createElement('option'); o.value = k; o.textContent = v.name; spotSel.appendChild(o);
  });
  spotSel.onchange = reloadAll; modelSel.onchange = reloadAll;
  reloadAll();
})();

function reloadAll() { loadForecast(); loadSessions(); }

// ---------- PRÉVISIONS ----------
function bestOfDay(evals, day) {
  const es = evals.filter(e => e.time.slice(0, 10) === day);
  const dl = es.filter(e => { const h = +e.time.slice(11, 13); return h >= 7 && h <= 21; });
  return (dl.length ? dl : es).reduce((a, b) => b.score > a.score ? b : a);
}

async function loadForecast() {
  const app = $('#forecast');
  app.innerHTML = '<div class="loading">Chargement des données de houle…</div>';
  const data = await (await fetch(`/api/forecast?spot=${spotSel.value}&model=${modelSel.value}`)).json();
  const evals = data.evals;
  if (!evals || !evals.length) { app.innerHTML = '<div class="loading">Pas de données.</div>'; return; }
  const days = [...new Set(evals.map(e => e.time.slice(0, 10)))];
  app.innerHTML = days.map(day => {
    const b = bestOfDay(evals, day), d = b.drivers;
    const dt = new Date(day + 'T12:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    const facts = [
      ['Énergie', `${d.energie.value} kW/m`, d.energie.label, Math.min(1, d.energie.score / 10)],
      ['Houle', `${d.houle.h} m @ ${d.houle.periode}s`, d.houle.label, d.houle.clean],
      ['Vent', `${Math.round(d.vent.speed)} km/h`, d.vent.label, d.vent.factor],
      ['Orientation', arrow(d.houle.dir), d.orientation.label, d.orientation.factor],
    ];
    const es = evals.filter(e => e.time.slice(0, 10) === day);
    const rows = es.filter(e => +e.time.slice(11, 13) % 3 === 0).map(e => `<tr>
      <td>${e.time.slice(11, 16)}</td>
      <td><span class="pill" style="background:${color(e.score)}22;color:${color(e.score)}">${e.score}</span></td>
      <td>${e.power} kW/m</td><td>${e.drivers.houle.h}m @ ${e.drivers.houle.periode}s</td>
      <td>${Math.round(e.drivers.vent.speed)}km/h ${e.drivers.vent.label}</td></tr>`).join('');
    return `<div class="day">
      <div class="dayhead">
        <div><div class="date">${dt}</div><div class="slot">meilleur créneau : ${b.time.slice(11, 16)}</div></div>
        <div class="score"><div class="gauge" style="--v:${b.score};--c:${color(b.score)}"><span>${b.score}</span></div><div class="lab">${b.label}</div></div>
      </div>
      <div class="explain">${md(b.explanation)}</div>
      <div class="drivers">${facts.map(([t, v, l, f]) => `<div class="drv"><div class="t">${t}</div><div class="v">${v}</div><div class="lab">${l}</div>
        <div class="bar"><i style="width:${Math.round(f * 100)}%;background:${fcolor(f)}"></i></div></div>`).join('')}</div>
      <details><summary>Détail heure par heure</summary>
        <table><tr><th>Heure</th><th>Note</th><th>Puissance</th><th>Houle</th><th>Vent</th></tr>${rows}</table></details>
    </div>`;
  }).join('');
}

// ---------- SESSIONS + VÉRIFICATION ----------
async function loadSessions() {
  const app = $('#sessions');
  app.innerHTML = '<div class="loading">Chargement du journal + hindcast…</div>';
  const data = await (await fetch(`/api/sessions?model=${modelSel.value}`)).json();
  let html = `<h2>Vérité terrain : ce que TU as vu vs ce que le modèle disait</h2>
    <p class="note">Pour chaque session loguée, on récupère ce que le modèle prévoyait ce jour-là (hindcast) et on compare à ton ressenti. C'est ça qui dit quel modèle croire sur ton spot.</p>`;
  html += data.rules.map(r => `<div class="rule">📌 <b>Règle apprise</b> — ${r.rule}<br><span class="note">${r.source}</span></div>`).join('');
  html += data.verifications.map(v => {
    const o = v.observed;
    const modelBlock = v.model_available ? `
      <div class="sesscol">
        <div class="lab">CE QUE LE MODÈLE DISAIT</div>
        <div class="big">${v.model_best_score}/10 <span class="note">(meilleur ${v.model_best_time})</span></div>
        <div>Vent modèle : ${arrow(v.model_wind_dir)} <b>${v.model_wind_label}</b></div>
        <div class="explain" style="font-size:13.5px">${md(v.model_explanation)}</div>
      </div>` : `<div class="sesscol"><div class="note">${v.note_model || ''}</div></div>`;
    const agreeColor = v.agreement === "d'accord" ? 'var(--good)' : v.agreement === 'écart moyen' ? 'var(--ok)' : 'var(--bad)';
    return `<div class="card">
      <div class="dayhead"><div class="date">${new Date(v.date + 'T12:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</div>
        <div class="lab">accord modèle/ressenti : <span class="agree" style="color:${agreeColor}">${v.agreement || '—'}</span></div></div>
      <div class="sess" style="margin-top:10px">
        <div class="sesscol">
          <div class="lab">CE QUE TU AS VU</div>
          <div class="big">${v.rating_obs}/5 <span class="note">${v.verdict_obs}</span></div>
          <div><span class="tag ${o.onshore ? 'bad' : 'good'}">${o.wind_txt}</span></div>
          <div style="margin-top:6px">🌊 ${o.size_txt} · ${o.break_txt}</div>
          <div class="note" style="margin-top:6px">${v.notes}</div>
        </div>
        ${modelBlock}
      </div></div>`;
  }).join('');
  html += `<div class="card"><b>Ce que la vérif révèle déjà</b><br>
    Le modèle a <b>bien vu le vent</b> les deux fois (offshore fin mai, onshore le 18/07) — c'est exactement ta règle.
    Mais son <b>score brut sous-note les petites houles propres</b> : pour ton niveau, <b>petit + offshore = super</b>, même si l'énergie physique est faible.
    → prochaine étape : recalibrer le score pour ton spot en donnant plus de poids au vent quand c'est petit.</div>`;
  app.innerHTML = html;
}

// ---------- SCIENCE (visualisations) ----------
let scienceDrawn = false;
function renderScience() {
  if (scienceDrawn) return; scienceDrawn = true;
  $('#science').innerHTML = SCIENCE_HTML;
  wireWaveGroups(); wirePeriodHeight(); drawRayleigh();
}

const SCIENCE_HTML = `
<h2>Pourquoi les vagues sont comme ça — la vraie physique (sourcée)</h2>
<p class="note">Contenu vérifié contre le Coastal Engineering Manual (USACE), Komar &amp; Gaughan 1972, Longuet-Higgins 1952, Battjes 1974. Détails + sources : <code>docs/physique-vagues-surf.md</code>.</p>

<h3>1. La période fait tout : longueur d'onde ∝ T²</h3>
<p>En eau profonde, la longueur d'onde et la vitesse ne dépendent QUE de la période (relation de dispersion d'Airy ω²=g·k) :</p>
<div class="formula">L₀ = g·T²/(2π) ≈ <b>1.56·T²</b> (m) &nbsp;|&nbsp; célérité c₀ = 1.56·T (m/s) &nbsp;|&nbsp; vitesse de groupe Cg = c₀/2 ≈ 0.78·T</div>
<div class="rule">🔧 <b>Correction de ta mémoire</b> — "L₀ = 1.28×H×T²" est faux : la longueur d'onde ne dépend <b>pas</b> de la hauteur H (théorie linéaire). Le "1.28" est un "1.56" corrompu (= g/2π), et le "×H" vient d'une contamination avec une formule d'<b>énergie</b> (où H entre, mais en H²). Ton "∝ T²" en revanche est <b>juste</b>.</div>

<div class="viz">
  <h3 style="margin-top:0">Même houle au large, période variable : hauteur qui déferle vs énergie</h3>
  <p class="note">On garde la <b>même houle au large</b> (H₀ = 1 m fixe → même énergie <i>par m²</i>) et on change la période. Deux choses grimpent, mais <b>pas au même rythme</b> — c'est là qu'était ta confusion sur les 20%.</p>
  <label>Période T = <span id="ph_t">10</span> s <input type="range" id="ph_range" min="4" max="20" value="10" step="0.5"></label>
  <div class="kfig">
    <div><div class="n" id="ph_L">156 m</div><div class="l">longueur d'onde L₀</div></div>
    <div><div class="n" id="ph_c">56 km/h</div><div class="l">vitesse de la houle</div></div>
    <div><div class="n" id="ph_Hb">— m</div><div class="l">hauteur déferlante Hb</div></div>
    <div><div class="n" id="ph_P">— kW/m</div><div class="l">puissance (énergie)</div></div>
  </div>
  <div class="kfig">
    <div><div class="n" id="ph_ghb" style="color:var(--ok)">—</div><div class="l">hauteur vs T=8s (∝ T⁰·⁴)</div></div>
    <div><div class="n" id="ph_gp" style="color:var(--good)">—</div><div class="l">énergie vs T=8s (∝ T)</div></div>
  </div>
  <canvas id="ph_canvas" width="900" height="200"></canvas>
  <div class="rule">🔧 <b>Tes "+20% par seconde"</b> : ça vaut pour l'<b>énergie</b> de la houle (P ∝ H²·T), pas pour la hauteur qui déferle. La hauteur ne gagne que <b>~+3–4% par seconde</b> (Hb ∝ T⁰·⁴, Komar-Gaughan), mais l'<b>énergie livrée explose</b> (~+8–12%/s). D'où : longue période = beaucoup plus de <b>jus</b>, un peu plus de <b>taille</b>.</div>
</div>

<h3>2. Houle vs mer du vent</h3>
<p>La <b>houle</b> (née d'une tempête lointaine, triée par la dispersion — les longues périodes voyagent plus vite et arrivent d'abord) est régulière, à crêtes longues, faible cambrure. La <b>mer du vent</b> (générée localement) est courte, raide, désorganisée — <b>ce que tu as eu</b>. Seuils pratiques (période de pic Tp) : <b>&lt;10 s</b> = mer du vent, <b>10–13 s</b> = houle limite, <b>&gt;14 s</b> = houle longue puissante.</p>

<h3>3. Types de déferlement & nombre d'Iribarren — d'où viennent les rouleaux</h3>
<p>Le type de déferlement = pente du fond vs cambrure de la houle, résumé par le nombre d'Iribarren :</p>
<div class="formula">ξ = tan(β) / √(H/L₀)   &nbsp;(tanβ = pente du fond, H/L₀ = cambrure)</div>
<table>
  <tr><th>Type</th><th>ξ₀ (au large)</th><th>Ce que ça donne</th></tr>
  <tr><td><b>Glissante</b> (spilling)</td><td>&lt; 0.5</td><td>mousse qui glisse, pas de tube. Pente douce + houle raide (courte période). Favorisée par l'onshore.</td></tr>
  <tr><td><b>Plongeante</b> (plunging)</td><td>0.5 – 3.3</td><td>🛢️ LE tube. Fond raide (récif/banc) et/ou houle longue peu cambrée. Favorisée par l'<b>offshore</b> (tient la lèvre).</td></tr>
  <tr><td><b>Gonflante</b> (surging)</td><td>&gt; 3.3</td><td>monte/descend sans vraiment casser. Plage très raide + houle très longue.</td></tr>
</table>
<div class="rule">🏄 <b>Pour tes beaux rouleaux à la Côte Sauvage</b> : il faut du <b>plongeant</b> = houle <b>longue période</b> (petit H/L₀) + <b>vent offshore</b> (de terre, qui retient la crête). C'est exactement ta règle de terrain, et voilà la physique : l'offshore ne "fait" pas la vague, il l'empêche de s'effondrer trop tôt et la garde creuse.</div>

<h3>4. La marée</h3>
<p>La marée change la <b>profondeur h</b> → déplace le point de déferlement et fait "sentir" à la vague une <b>pente locale différente</b> (donc un ξ différent → la même houle peut être molle à une marée et creuse à une autre). Trop d'eau (haute) = vagues grasses qui ne sentent pas le fond ; trop peu (basse) = ça ferme/vidange ; <b>mi-marée montante</b> = souvent l'optimum sur un beach break (le point de déferlement tombe sur le raidissement du banc, et l'eau qui pousse ajoute de l'organisation).</p>

<div class="viz">
  <h3 style="margin-top:0">Les vagues arrivent en séries (sets) = battements de sinusoïdes</h3>
  <p class="note">✅ Ton intuition "modulation AM" est <b>exacte</b> : deux trains de houle de fréquences proches → cos·cos = une <b>porteuse</b> rapide × une <b>enveloppe</b> lente. Et comme l'énergie voyage à Cg = c/2 (moitié de la vitesse des crêtes), elle se regroupe → les grosses arrivent par <b>séries</b>.</p>
  <label>Écart de période entre les deux houles <input type="range" id="wg_range" min="1" max="30" value="12"></label>
  <canvas id="wg_canvas" width="900" height="220"></canvas>
</div>

<h3>5. Toutes les vagues n'ont pas la même taille : loi de Rayleigh</h3>
<p>✅ Tu avais raison : les hauteurs suivent une <b>distribution de Rayleigh</b> (pas normale, pas Poisson, pas exponentielle). L'élévation de la surface, elle, est gaussienne ; c'est la <i>hauteur</i> crête-à-creux qui est Rayleigh (Longuet-Higgins 1952).</p>
<div class="formula">Hs (significative) = moyenne du <b>tiers</b> le plus haut = H₁/₃ &nbsp;|&nbsp; H₁/₁₀ ≈ <b>1.27·Hs</b> &nbsp;|&nbsp; Hmax ≈ 1.86–2.0·Hs (sur 1000–3000 vagues)</div>
<div class="viz">
  <canvas id="ray_canvas" width="900" height="220"></canvas>
  <p class="note">Aire sous la courbe = probabilité. Les 10% les plus grosses (H₁/₁₀) sont ~27% plus hautes que Hs : d'où le fait d'attendre "la bonne série". C'est aussi pourquoi les prévis parlent de Hs (moyenne du tiers haut) et pas de la vague moyenne.</p>
</div>

<h3>6. Sous l'eau : mouvement orbital</h3>
<p>En eau profonde l'eau décrit des <b>orbites circulaires</b> dont le rayon décroît en <b>e^(k·z)</b> avec la profondeur : à une demi-longueur d'onde (z = −L/2) il ne reste que <b>e^(−π) ≈ 4%</b> du mouvement → c'est la "base des vagues". Près du bord (eau peu profonde) les orbites s'aplatissent en ellipses et <b>touchent le fond</b> (va-et-vient horizontal) → c'est ça qui déclenche shoaling, réfraction et déferlement. Une houle longue "sent" le fond plus au large → plus de shoaling → déferle plus gros.</p>

<h3>7. Comment font les experts (la checklist)</h3>
<ol>
  <li><b>Un report tout fait</b> pour la tendance (montée/baisse, fenêtre de vent).</li>
  <li><b>Cartes de pression</b> : repérer la dépression atlantique qui génère la houle (isobares serrées = vent fort ; anticyclone = calme/offshore mais pas de houle).</li>
  <li><b>Cartes de période/énergie</b> + sorties modèle : longue période = groundswell puissant. Temps de trajet ≈ distance / (1.5×Tp nœuds).</li>
  <li><b>Bouées houlographes</b> (CANDHIS en France) : comparer prévu vs mesuré en temps réel — <b>exactement ce que fait ton onglet "vérité terrain"</b>.</li>
  <li><b>Webcams</b> : la vérité que les modèles ne donnent pas.</li>
  <li><b>Spectre directionnel</b> : pic étroit = houle propre d'une seule tempête ; tache large = mer du vent / mers croisées.</li>
</ol>
`;

// --- viz : période -> hauteur déferlante (Komar T^0.4) vs énergie (P ∝ T) ---
function wirePeriodHeight() {
  const H0 = 1.0;                         // houle au large fixe (m) = même énergie/m²
  const r = $('#ph_range'), cv = $('#ph_canvas'), ctx = cv.getContext('2d');
  const breakerH = T => { const L0 = 1.56 * T * T; return H0 * 0.56 * Math.pow(H0 / L0, -0.2); }; // ∝ T^0.4
  const power = T => 0.49 * H0 * H0 * T;  // kW/m, ∝ T à H0 fixe
  const Hb8 = breakerH(8), P8 = power(8);
  function upd() {
    const T = +r.value, L0 = 1.56 * T * T, c = 1.56 * T * 3.6, Hb = breakerH(T), P = power(T);
    $('#ph_t').textContent = T; $('#ph_L').textContent = Math.round(L0) + ' m';
    $('#ph_c').textContent = Math.round(c) + ' km/h'; $('#ph_Hb').textContent = Hb.toFixed(2) + ' m';
    $('#ph_P').textContent = P.toFixed(1) + ' kW/m';
    const gh = (Hb / Hb8 - 1) * 100, gp = (P / P8 - 1) * 100;
    $('#ph_ghb').textContent = (gh >= 0 ? '+' : '') + Math.round(gh) + '%';
    $('#ph_gp').textContent = (gp >= 0 ? '+' : '') + Math.round(gp) + '%';
    ctx.clearRect(0, 0, cv.width, cv.height);
    const mid = cv.height / 2, amp = Math.min(85, Hb * 45), wl = Math.max(60, cv.width * (L0 / 400));
    ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2; ctx.beginPath();
    for (let x = 0; x <= cv.width; x++) { const y = mid - amp * Math.sin(2 * Math.PI * x / wl); x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.stroke();
    ctx.fillStyle = '#8aa4bd'; ctx.font = '12px system-ui';
    ctx.fillText(`H₀ (large) = ${H0} m fixe · L₀ = ${Math.round(L0)} m · Hb = ${Hb.toFixed(2)} m · P = ${P.toFixed(1)} kW/m`, 10, 18);
  }
  r.oninput = upd; upd();
}

// --- viz : groupes de vagues / battements ---
function wireWaveGroups() {
  const r = $('#wg_range'), cv = $('#wg_canvas'), ctx = cv.getContext('2d');
  function upd() {
    const dT = +r.value / 100;            // écart de fréquence
    ctx.clearRect(0, 0, cv.width, cv.height);
    const mid = cv.height / 2, f1 = 0.06, f2 = 0.06 + dT / 10;
    // enveloppe
    ctx.strokeStyle = '#ff6b6b'; ctx.lineWidth = 1.5; ctx.beginPath();
    for (let x = 0; x <= cv.width; x++) { const env = 70 * Math.abs(Math.cos(Math.PI * (f1 - f2) * x)); const y = mid - env; x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.stroke(); ctx.beginPath();
    for (let x = 0; x <= cv.width; x++) { const env = 70 * Math.abs(Math.cos(Math.PI * (f1 - f2) * x)); const y = mid + env; x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.stroke();
    // somme des deux houles
    ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2; ctx.beginPath();
    for (let x = 0; x <= cv.width; x++) { const y = mid - 35 * (Math.sin(2 * Math.PI * f1 * x) + Math.sin(2 * Math.PI * f2 * x)); x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.stroke();
    ctx.fillStyle = '#8aa4bd'; ctx.font = '12px system-ui';
    ctx.fillText('bleu = somme des 2 houles · rouge = enveloppe (les sets)', 10, 16);
  }
  r.oninput = upd; upd();
}

// --- viz : distribution de Rayleigh ---
function drawRayleigh() {
  const cv = $('#ray_canvas'), ctx = cv.getContext('2d');
  const Hs = 2.0, sigma = Hs / 2, W = cv.width, H = cv.height, m = 30;
  const pdf = h => (h / (sigma * sigma)) * Math.exp(-h * h / (2 * sigma * sigma));
  const hmax = 6; let peak = 0;
  for (let h = 0; h < hmax; h += 0.02) peak = Math.max(peak, pdf(h));
  const X = h => m + (h / hmax) * (W - 2 * m), Y = p => H - m - (p / peak) * (H - 2 * m);
  ctx.clearRect(0, 0, W, H);
  // aire
  ctx.fillStyle = '#38bdf822'; ctx.beginPath(); ctx.moveTo(X(0), Y(0));
  for (let h = 0; h <= hmax; h += 0.02) ctx.lineTo(X(h), Y(pdf(h)));
  ctx.lineTo(X(hmax), Y(0)); ctx.fill();
  ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2; ctx.beginPath();
  for (let h = 0; h <= hmax; h += 0.02) { const x = X(h), y = Y(pdf(h)); h ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
  ctx.stroke();
  // repères
  const marks = [[Hs * 0.706, 'Hrms', '#8aa4bd'], [Hs, 'Hs', '#f6c945'], [Hs * 1.27, 'H1/10', '#37d67a'], [Hs * 1.8, 'Hmax', '#ff6b6b']];
  ctx.font = '12px system-ui';
  marks.forEach(([h, lab, col]) => {
    ctx.strokeStyle = col; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(X(h), Y(0)); ctx.lineTo(X(h), Y(peak) - 4); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = col; ctx.fillText(lab, X(h) - 8, Y(peak) - 8);
  });
  ctx.fillStyle = '#8aa4bd'; ctx.fillText('hauteur des vagues →', W - 150, H - 10);
}
