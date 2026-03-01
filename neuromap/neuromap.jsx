/**
 * EGON NeuroMap v7 — Deep-Dive Neural Visualization
 *
 * KEINE Fake-Nodes. Jedes visuelle Element = echte Daten:
 *
 * - Region-Kugeln (10) = echte Hirnregionen, Groesse = Aktivitaet
 * - Faeden (Bezier-Kurven) = echte neuronale Verbindungen aus /brain/snapshot
 *   -> Dicke/Farbe/Opacity direkt aus der API
 * - Bond-Nodes = echte Beziehungen, Groesse = Bond-Score
 *   -> Klick zeigt Partner, Trust, History, Narben
 * - Drive-Nodes = echte Panksepp-Drives aus DNA
 *   -> Groesse = Drive-Staerke
 *
 * v7 FEATURES:
 * - Anatomically correct region positions
 * - Translucent brain shell (ellipsoid + wireframe)
 * - Bezier curve threads (QuadraticBezierCurve3)
 * - NO auto-zoom on click (user-initiated zoom only via "Hierher zoomen" button)
 * - Formation Paths: animated neural pathway highlighting on click
 * - Search bar with debounce + result highlighting
 * - Enhanced detail panels for all sub-node types
 * - Smooth camera system with 3 zoom levels (overview / region / item)
 * - Double-click region -> deep dive with sub-nodes from API
 * - Breadcrumb navigation + Escape key
 * - Grey synapses with impulse highlighting
 * - Path impulse animations (synapse paths)
 *
 * VISUELLER ALTERS-EFFEKT:
 * - Junger EGON: wenige duenne Faeden, kleine Bond-Nodes -> sparsames Gehirn
 * - Alter EGON: viele dicke Faeden, grosse Bond-Nodes -> dichtes Netzwerk
 * - Sofort erkennbar auf einen Blick!
 */

var useState = React.useState;
var useEffect = React.useEffect;
var useRef = React.useRef;
var useCallback = React.useCallback;

// ============================================================
// THEMES
// ============================================================
var THEMES = {
  dark: {
    bg: "#0d1017", fog: "#0d1017", fogDensity: 0.025,
    text: "#dde0ec", textMid: "#8890aa", textDim: "#4a5270",
    accent: "#5e7ce0",
    regionGlow: 0.4, regionOp: 0.7,
    threadFlash: 0.9,
    dimOp: 0.08,
  },
  light: {
    bg: "#eef0f6", fog: "#eef0f6", fogDensity: 0.02,
    text: "#1a1e30", textMid: "#5a6280", textDim: "#9098b0",
    accent: "#4060d8",
    regionGlow: 0.25, regionOp: 0.8,
    threadFlash: 0.8,
    dimOp: 0.15,
  },
};

// ============================================================
// REGIONEN — anatomically correct positions
// ============================================================
var REGIONS = {
  praefrontal:  { hex: "#a78bfa", label: "Ego-Kern", sub: "DNA & Entscheidung (Praefrontaler Kortex)", pos: [0.0, 1.0, 1.8] },
  amygdala:     { hex: "#4ade80", label: "Emotionaler Kern", sub: "Primaer-Emotionen (Amygdala)", pos: [-0.8, -0.3, 0.5] },
  hippocampus:  { hex: "#2dd4bf", label: "Gedaechtnis-Speicher", sub: "Episoden & Erlebnisse (Hippocampus)", pos: [-0.6, -0.5, -0.2] },
  neokortex:    { hex: "#60a5fa", label: "Langzeit-Archiv", sub: "Sparks & Wissen (Neokortex)", pos: [0.0, 1.6, 0.0] },
  insula:       { hex: "#f472b6", label: "Somatic Gate", sub: "Koerper & Marker (Insula)", pos: [-0.9, 0.1, 0.3] },
  thalamus:     { hex: "#94a3b8", label: "Bewusstseins-Relay", sub: "Thalamus-Filter (Thalamus)", pos: [0.0, 0.0, 0.0] },
  hypothalamus: { hex: "#fbbf24", label: "Drive-Zentrum", sub: "Panksepp-Drives (Hypothalamus)", pos: [0.0, -0.4, 0.3] },
  hirnstamm:    { hex: "#8d6e63", label: "Grundfunktionen", sub: "Energie & Zirkadian (Hirnstamm)", pos: [0.0, -1.4, -0.8] },
  cerebellum:   { hex: "#78909c", label: "Koordination", sub: "Motorik & Balance (Cerebellum)", pos: [0.0, -1.2, -1.4] },
  bonds:        { hex: "#fb923c", label: "Bindungs-Zentrum", sub: "Bonds & Beziehungen (Temporalpol)", pos: [1.0, -0.2, 1.0] },
};

var EGON_NAMES = {
  adam_001: 'Adam', eva_002: 'Eva', lilith_003: 'Lilith',
  marx_004: 'Marx', ada_005: 'Ada', parzival_006: 'Parzival',
  sokrates_007: 'Sokrates', leibniz_008: 'Leibniz',
  goethe_009: 'Goethe', eckhart_010: 'Eckhart',
};

// ============================================================
// FORMATION PATHS — named neural pathways for each data type
// ============================================================
var FORMATION_PATHS = {
  bond:          { path: ['hirnstamm','thalamus','amygdala','praefrontal','bonds'], color: '#fb923c', label: 'Bond-Bildung' },
  episode:       { path: ['thalamus','amygdala','hippocampus','praefrontal'], color: '#2dd4bf', label: 'Episoden-Bildung' },
  emotion:       { path: ['thalamus','amygdala','insula','praefrontal'], color: '#4ade80', label: 'Emotions-Verarbeitung' },
  drive:         { path: ['hypothalamus','amygdala','praefrontal'], color: '#fbbf24', label: 'Antrieb-Aktivierung' },
  drive_gauge:   { path: ['hypothalamus','amygdala','praefrontal'], color: '#fbbf24', label: 'Antrieb-Aktivierung' },
  skill:         { path: ['neokortex','cerebellum','hippocampus','praefrontal'], color: '#60a5fa', label: 'Skill-Lernen' },
  experience:    { path: ['thalamus','neokortex','hippocampus','praefrontal'], color: '#60a5fa', label: 'Erfahrungs-Speicherung' },
  text:          { path: ['hippocampus','thalamus','praefrontal','neokortex'], color: '#a78bfa', label: 'Gedaechtnis-Abruf' },
  somatic_gate:  { path: ['amygdala','hypothalamus','hirnstamm','insula'], color: '#f472b6', label: 'Koerper-Reaktion' },
  metacognition: { path: ['praefrontal','hippocampus','amygdala','insula'], color: '#c084fc', label: 'Selbstreflexion' },
  dna_profile:   { path: ['hirnstamm','thalamus','praefrontal'], color: '#f97316', label: 'DNA-Identitaet' },
  circadian:     { path: ['hirnstamm','hypothalamus','thalamus'], color: '#fbbf24', label: 'Zirkadian-Rhythmus' },
  routing:       { path: ['thalamus','praefrontal','amygdala'], color: '#f59e0b', label: 'Routing-Entscheidung' },
  decision:      { path: ['thalamus','amygdala','praefrontal'], color: '#ef4444', label: 'Kalibrierung' },
  survive:       { path: ['hirnstamm','hypothalamus','amygdala','insula'], color: '#10b981', label: 'Ueberlebens-Check' },
  thrive:        { path: ['praefrontal','amygdala','hippocampus'], color: '#a78bfa', label: 'Entfaltungs-Check' },
  lebensfaden:   { path: ['cerebellum','hippocampus','praefrontal'], color: '#a78bfa', label: 'Muster-Erkennung' },
  pairing:       { path: ['hirnstamm','amygdala','hypothalamus','bonds'], color: '#e91e63', label: 'Paarungs-Prozess' },
  diary:         { path: ['praefrontal','hippocampus','bonds'], color: '#ffd54f', label: 'Tagebuch-Eintrag' },
  cue_index:     { path: ['hippocampus','thalamus','neokortex'], color: '#fbbf24', label: 'Cue-Indexierung' },
  gravity:       { path: ['amygdala','hypothalamus','praefrontal','insula'], color: '#fbbf24', label: 'Emotionale Gravitation' },
  unknown:       { path: ['thalamus','praefrontal'], color: '#8890aa', label: 'Neurale Verarbeitung' },
};

// Thread category -> formation path mapping
var THREAD_CATEGORY_MAP = {
  bond: 'bond',
  emotion: 'emotion',
  episode: 'episode',
  drive: 'drive',
  skill: 'skill',
  experience: 'experience',
  text: 'text',
  somatic: 'somatic_gate',
  circadian: 'circadian',
  routing: 'routing',
  decision: 'decision',
  survive: 'survive',
  thrive: 'thrive',
  pairing: 'pairing',
  diary: 'diary',
};

// ============================================================
// IMPULSE SYSTEM (enhanced with formation path firing)
// ============================================================
function ThreadImpulseSystem() {
  this.impulses = [];
  this.id = 0;
  this.activeFormationPath = null;
  this._formationTimer = null;
  this._formationClearTimer = null;
}

ThreadImpulseSystem.prototype.fire = function(threadIdx, color, speed) {
  this.impulses.push({
    id: this.id++, threadIdx: threadIdx, color: color,
    progress: 0, speed: speed || (0.8 + Math.random() * 1.2),
  });
};

ThreadImpulseSystem.prototype.firePath = function(pathRegions, color, speed, sceneData, threadLines) {
  if (!sceneData || !threadLines || pathRegions.length < 2) return;
  var self = this;
  var segments = [];
  for (var i = 0; i < pathRegions.length - 1; i++) {
    var from = pathRegions[i];
    var to = pathRegions[i + 1];
    threadLines.forEach(function(tl, idx) {
      var t = tl.thread;
      if ((t.von === from && t.nach === to) || (t.von === to && t.nach === from)) {
        segments.push({ idx: idx, delay: i });
      }
    });
  }
  segments.forEach(function(seg) {
    setTimeout(function() {
      self.fire(seg.idx, color, speed);
    }, seg.delay * 300);
  });
};

ThreadImpulseSystem.prototype.fireFormationPath = function(pathDef, sceneData, threadLines) {
  if (!pathDef || !pathDef.path || pathDef.path.length < 2) return;
  var self = this;

  // Clear any existing formation
  if (self._formationTimer) clearTimeout(self._formationTimer);
  if (self._formationClearTimer) clearTimeout(self._formationClearTimer);

  self.activeFormationPath = {
    regions: pathDef.path.slice(),
    color: pathDef.color,
    label: pathDef.label,
    litRegions: {},
    startTime: Date.now(),
  };

  // Stagger 300ms per segment: each region lights up sequentially
  var totalDelay = 0;
  for (var i = 0; i < pathDef.path.length; i++) {
    (function(regionKey, delay) {
      setTimeout(function() {
        if (self.activeFormationPath) {
          self.activeFormationPath.litRegions[regionKey] = true;
        }
      }, delay);
    })(pathDef.path[i], i * 300);
    totalDelay = i * 300;
  }

  // Fire thread impulses between consecutive path regions
  self.firePath(pathDef.path, pathDef.color, 0.6, sceneData, threadLines);

  // Auto-clear after animation + 3s
  self._formationClearTimer = setTimeout(function() {
    self.activeFormationPath = null;
  }, totalDelay + 3000);
};

ThreadImpulseSystem.prototype.isRegionInFormationPath = function(regionKey) {
  if (!this.activeFormationPath) return false;
  return !!this.activeFormationPath.litRegions[regionKey];
};

ThreadImpulseSystem.prototype.getFormationPathLabel = function() {
  if (!this.activeFormationPath) return null;
  return this.activeFormationPath.label;
};

ThreadImpulseSystem.prototype.getFormationColor = function() {
  if (!this.activeFormationPath) return null;
  return this.activeFormationPath.color;
};

ThreadImpulseSystem.prototype.update = function(dt) {
  this.impulses = this.impulses.filter(function(imp) {
    imp.progress += imp.speed * dt;
    return imp.progress < 1.0;
  });
};

ThreadImpulseSystem.prototype.getGlow = function(threadIdx) {
  var maxGlow = 0;
  for (var ii = 0; ii < this.impulses.length; ii++) {
    var imp = this.impulses[ii];
    if (imp.threadIdx !== threadIdx) continue;
    var g = Math.sin(imp.progress * Math.PI);
    maxGlow = Math.max(maxGlow, g);
  }
  return maxGlow;
};

// ============================================================
// BUILD SCENE FROM API DATA
// ============================================================
function buildSceneData(apiData) {
  // --- 1. Region-Nodes (echte Regionen) ---
  var regionNodes = [];
  var regionMap = {};

  var usedRegions = new Set();
  if (apiData.snapshot && apiData.snapshot.faeden) {
    for (var fi = 0; fi < apiData.snapshot.faeden.length; fi++) {
      var f = apiData.snapshot.faeden[fi];
      usedRegions.add(f.von);
      usedRegions.add(f.nach);
    }
  }
  var regionKeys = Object.keys(REGIONS);
  for (var rki = 0; rki < regionKeys.length; rki++) {
    usedRegions.add(regionKeys[rki]);
  }

  var nodeIdx = 0;
  usedRegions.forEach(function(rk) {
    var def = REGIONS[rk];
    if (!def) return;
    regionMap[rk] = nodeIdx;
    var rd = null;
    if (apiData.regions && apiData.regions.regionen) {
      rd = apiData.regions.regionen.find(function(r) { return r.region === rk; });
    }
    regionNodes.push({
      id: nodeIdx++,
      type: 'region',
      region: rk,
      label: def.label,
      sub: def.sub,
      hex: def.hex,
      pos: def.pos,
      intensity: rd ? (rd.intensitaet || 0) : 0,
      nutzung: rd ? (rd.nutzung || 0) : 0,
      size: 0.12 + ((rd ? rd.intensitaet : 0) || 0) * 0.15,
    });
  });

  // --- 2. Faeden (echte Verbindungen) ---
  var threads = [];
  if (apiData.snapshot && apiData.snapshot.faeden) {
    for (var ffi = 0; ffi < apiData.snapshot.faeden.length; ffi++) {
      var ff = apiData.snapshot.faeden[ffi];
      var vonIdx = regionMap[ff.von];
      var nachIdx = regionMap[ff.nach];
      if (vonIdx === undefined || nachIdx === undefined) continue;
      threads.push({
        id: 'thread_' + threads.length,
        fadenId: ff.faden_id,
        kategorie: ff.kategorie,
        von: ff.von,
        nach: ff.nach,
        vonIdx: vonIdx, nachIdx: nachIdx,
        dicke: ff.dicke,
        farbe: ff.farbe,
        opacity: ff.opacity,
        permanent: ff.permanent,
        meta: ff.meta || {},
        label: _threadLabel(ff),
      });
    }
  }

  // --- 3. Bond-Nodes (echte Beziehungen) ---
  var bondNodes = [];
  if (apiData.bonds && apiData.bonds.bonds) {
    var bondsCenter = REGIONS.bonds ? REGIONS.bonds.pos : [1.0, -0.2, 1.0];
    apiData.bonds.bonds.forEach(function(bond, i) {
      var angle = (i / Math.max(apiData.bonds.bonds.length, 1)) * Math.PI * 1.5 - Math.PI * 0.25;
      var radius = 0.4 + bond.staerke * 0.5;
      var entityType = bond.bond_type || 'egon';
      var entityLabel = entityType === 'person' ? 'Mensch' : entityType === 'owner' ? 'Bezugsperson' : 'EGON';
      var entityColor = entityType === 'person' ? '#fb923c' : entityType === 'owner' ? '#ffd700' : '#7db4e0';
      bondNodes.push({
        id: nodeIdx++,
        type: 'bond',
        label: bond.partner_name || bond.partner_id,
        bond_typ: bond.bond_typ,
        bond_type: entityType,
        entity_label: entityLabel,
        entity_color: entityColor,
        contact_status: bond.contact_status || 'verified',
        score: bond.score,
        staerke: bond.staerke,
        trust: bond.trust,
        familiarity: bond.familiarity,
        hat_narbe: bond.hat_narbe,
        attachment: bond.attachment_style,
        history: bond.history || [],
        observations: bond.observations || [],
        emotional_debt: bond.emotional_debt || 0,
        last_interaction: bond.last_interaction,
        chat_count: bond.chat_count || 0,
        first_interaction: bond.first_interaction || null,
        social_map: bond.social_map || null,
        resonanz: bond.resonanz || null,
        hex: entityColor,
        region: 'bonds',
        pos: [
          bondsCenter[0] + Math.cos(angle) * radius,
          bondsCenter[1] + Math.sin(angle) * 0.5,
          bondsCenter[2] + Math.sin(angle) * radius * 0.5,
        ],
        size: 0.06 + bond.staerke * 0.12,
        faden: bond.faden,
      });
    });
  }

  // --- 4. Drive-Nodes (echte Panksepp-Drives) ---
  var driveNodes = [];
  if (apiData.dna && apiData.dna.dominant_drives) {
    var driveCenter = REGIONS.praefrontal ? REGIONS.praefrontal.pos : [0.0, 1.0, 1.8];
    var driveColors = {
      SEEKING: '#facc15', PLAY: '#4ade80', CARE: '#f472b6',
      PANIC: '#ef4444', RAGE: '#dc2626', FEAR: '#a78bfa',
      LUST: '#ec4899', LEARNING: '#60a5fa',
    };
    apiData.dna.dominant_drives.forEach(function(d, i) {
      var angle = (i / Math.max(apiData.dna.dominant_drives.length, 1)) * Math.PI - Math.PI * 0.5;
      driveNodes.push({
        id: nodeIdx++,
        type: 'drive',
        label: d.drive,
        value: d.value,
        hex: driveColors[d.drive] || '#5e7ce0',
        region: 'praefrontal',
        pos: [
          driveCenter[0] + Math.cos(angle) * 0.5,
          driveCenter[1] + 0.5 + i * 0.25,
          driveCenter[2] + Math.sin(angle) * 0.3,
        ],
        size: 0.04 + d.value * 0.06,
      });
    });
  }

  var allNodes = regionNodes.concat(bondNodes).concat(driveNodes);

  // --- 5. Statistik ---
  var stats = (apiData.snapshot && apiData.snapshot.statistik) ? apiData.snapshot.statistik : {};
  var complexity = threads.length + bondNodes.length + driveNodes.length;

  return { regionNodes: regionNodes, bondNodes: bondNodes, driveNodes: driveNodes, allNodes: allNodes, threads: threads, regionMap: regionMap, stats: stats, complexity: complexity };
}

function _threadLabel(f) {
  if (f.kategorie === 'bond' && f.meta && f.meta.partner) {
    return 'Bond: ' + f.meta.partner + ' (' + f.meta.bond_typ + ', ' + Math.round(f.meta.bond_staerke * 100) + '%)';
  }
  var von = f.von.charAt(0).toUpperCase() + f.von.slice(1);
  var nach = f.nach.charAt(0).toUpperCase() + f.nach.slice(1);
  return von + ' \u2192 ' + nach + ' (' + f.kategorie + ', Dicke: ' + f.dicke.toFixed(2) + ')';
}

// ============================================================
// DETAIL PANEL RENDERERS (for sub-node types) — Enhanced v7
// ============================================================
function renderSubNodeDetail(info, T, onZoomTo, onFireFormation) {
  if (!info || !info.detail) return null;
  var detail = info.detail;

  // Helper: gauge bar element
  function gaugeBar(value, color, label) {
    var pct = Math.max(0, Math.min(1, value || 0)) * 100;
    return React.createElement('div', { style: { marginTop: 4 } },
      label && React.createElement('div', { style: { color: T.textDim, fontSize: 9, marginBottom: 2 } }, label),
      React.createElement('div', { className: 'gauge-bar' },
        React.createElement('div', { className: 'gauge-fill', style: { width: pct + '%', background: color || '#5e7ce0' } })
      ),
      React.createElement('div', { style: { color: T.text, fontSize: 9, marginTop: 1 } }, pct.toFixed(0) + '%')
    );
  }

  // Helper: action buttons (zoom + formation path)
  function actionButtons(subType) {
    var pathDef = FORMATION_PATHS[subType] || FORMATION_PATHS.unknown;
    return React.createElement('div', { style: { display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' } },
      onZoomTo && React.createElement('button', { className: 'zoom-btn', onClick: function() { onZoomTo(info); } }, 'Hierher zoomen'),
      onFireFormation && React.createElement('button', { className: 'formation-btn', onClick: function() { onFireFormation(pathDef); } },
        '\u26A1 Entstehungspfad zeigen')
    );
  }

  // Bond sub-node
  if (info.subType === 'bond') {
    return React.createElement('div', { style: { marginTop: 8 } },
      // Score bar
      detail.score != null && gaugeBar(detail.staerke || detail.score / 100, info.hex || '#fb923c', 'Score'),
      // Trust bar
      detail.trust != null && gaugeBar(detail.trust, '#4ade80', 'Trust'),
      // Resonanz bar (if pairing)
      detail.resonanz != null && gaugeBar(detail.resonanz, '#e91e63', 'Resonanz'),
      // Bond typ
      detail.bond_typ && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 4 } },
        'Typ: ', detail.bond_typ
      ),
      // Attachment
      detail.attachment_style && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } },
        'Attachment: ', detail.attachment_style
      ),
      // Narbe warning
      detail.hat_narbe && React.createElement('div', { style: { color: '#ef4444', fontSize: 9, marginTop: 4, padding: '3px 6px', background: 'rgba(239,68,68,0.1)', borderRadius: 4, display: 'inline-block' } },
        '\u26A0 Hat Narbe'
      ),
      // Chat count + first interaction
      (detail.chat_count || detail.first_interaction) && React.createElement('div', { style: { fontSize: 9, color: T.textDim, marginTop: 4 } },
        detail.chat_count ? ('Chats: ' + detail.chat_count) : '',
        detail.first_interaction ? (' \u00B7 Erstes Treffen: ' + detail.first_interaction) : ''
      ),
      // Social map
      detail.social_map && React.createElement('div', { className: 'social-card', style: { marginTop: 6 } },
        React.createElement('div', { className: 'panel-header' }, 'Social Map'),
        detail.social_map.erster_eindruck && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } },
          'Erster Eindruck: ', detail.social_map.erster_eindruck),
        detail.social_map.aktueller_eindruck && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } },
          'Aktueller Eindruck: ', detail.social_map.aktueller_eindruck)
      ),
      // Observations (scrollable, max-height 200px)
      detail.observations && detail.observations.length > 0 && React.createElement('div', { style: { marginTop: 8, borderTop: '1px solid rgba(90,110,170,0.1)', paddingTop: 6 } },
        React.createElement('div', { className: 'panel-header' }, 'Beobachtungen (' + detail.observations.length + ')'),
        React.createElement('div', { className: 'obs-scroll' },
          detail.observations.map(function(obs, i) {
            return React.createElement('div', { key: i, style: { fontSize: 9, color: T.textMid, marginBottom: 3, lineHeight: 1.3, paddingLeft: 8, borderLeft: '2px solid ' + (info.hex || '#fb923c') + '33' } }, obs);
          })
        )
      ),
      // History timeline
      detail.history && detail.history.length > 0 && React.createElement('div', { style: { marginTop: 8, borderTop: '1px solid rgba(90,110,170,0.1)', paddingTop: 6 } },
        React.createElement('div', { className: 'panel-header' }, 'Geschichte (' + detail.history.length + ')'),
        detail.history.slice(-8).map(function(h, i) {
          var delta = (h.trust_after || 0) - (h.trust_before || 0);
          return React.createElement('div', { key: i, className: 'history-item' },
            React.createElement('div', { className: 'history-date' }, h.date || ''),
            React.createElement('div', { style: { color: T.textMid } }, (h.event || '').slice(0, 80)),
            delta !== 0 && React.createElement('span', { className: delta > 0 ? 'history-delta-pos' : 'history-delta-neg' },
              ' Trust: ' + (h.trust_before || 0) + ' \u2192 ' + (h.trust_after || 0))
          );
        })
      ),
      actionButtons('bond')
    );
  }

  // Emotion sub-node
  if (info.subType === 'emotion') {
    return React.createElement('div', { style: { marginTop: 8 } },
      detail.intensity != null && gaugeBar(detail.intensity, info.hex || '#4ade80', 'Intensitaet'),
      detail.cause && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 4 } }, 'Ursache: ', detail.cause),
      detail.decay_class && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } }, 'Decay: ', detail.decay_class),
      detail.verbal_anchor && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2, fontStyle: 'italic' } }, '"', detail.verbal_anchor, '"'),
      actionButtons('emotion')
    );
  }

  // Drive / drive_gauge sub-node
  if (info.subType === 'drive' || info.subType === 'drive_gauge') {
    var driveVal = detail.value != null ? detail.value : detail.staerke;
    return React.createElement('div', { style: { marginTop: 8 } },
      React.createElement('div', { style: { color: info.hex, fontSize: 24, fontWeight: 700 } },
        driveVal != null ? (driveVal * 100).toFixed(0) + '%' : '-'
      ),
      driveVal != null && gaugeBar(driveVal, info.hex || '#fbbf24', null),
      detail.drive && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 4 } }, 'Drive: ', detail.drive),
      detail.beschreibung && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2, lineHeight: 1.4 } }, detail.beschreibung),
      actionButtons('drive')
    );
  }

  // Episode sub-node
  if (info.subType === 'episode') {
    return React.createElement('div', { style: { marginTop: 8 } },
      detail.date && React.createElement('div', { style: { fontSize: 9, color: T.textDim } }, detail.date),
      detail.type && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } }, 'Typ: ', detail.type),
      detail.with && React.createElement('div', { style: { fontSize: 10, color: T.text, marginTop: 2 } }, 'Mit: ', detail.with),
      detail.thread_title && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } }, 'Faden: ', detail.thread_title),
      // Full summary (scrollable)
      detail.summary && React.createElement('div', { className: 'detail-text-area', style: { marginTop: 6, maxHeight: 200 } }, detail.summary),
      // ALL emotions as color-coded gauge bars
      detail.emotions_felt && Object.keys(detail.emotions_felt).length > 0 && React.createElement('div', { style: { marginTop: 6 } },
        React.createElement('div', { className: 'panel-header' }, 'Emotionen'),
        Object.entries(detail.emotions_felt).map(function(pair) {
          var emotionColors = {
            freude: '#4ade80', trauer: '#60a5fa', angst: '#a78bfa', wut: '#ef4444',
            ekel: '#78909c', ueberraschung: '#fbbf24', neugier: '#facc15', liebe: '#f472b6',
            scham: '#8d6e63', stolz: '#fb923c',
          };
          var eColor = emotionColors[pair[0].toLowerCase()] || '#5e7ce0';
          return React.createElement('div', { key: pair[0], style: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 } },
            React.createElement('span', { style: { fontSize: 9, color: T.textMid, width: 70, textAlign: 'right' } }, pair[0]),
            React.createElement('div', { className: 'gauge-bar', style: { flex: 1 } },
              React.createElement('div', { className: 'gauge-fill', style: { width: (pair[1] * 100) + '%', background: eColor } })
            ),
            React.createElement('span', { style: { fontSize: 8, color: T.textDim, width: 28 } }, (pair[1] * 100).toFixed(0) + '%')
          );
        })
      ),
      // Significance gauge
      detail.significance != null && gaugeBar(detail.significance, '#fbbf24', 'Bedeutung'),
      // Tags as chips
      detail.tags && detail.tags.length > 0 && React.createElement('div', { style: { marginTop: 4, display: 'flex', flexWrap: 'wrap' } },
        detail.tags.map(function(tag, i) {
          return React.createElement('span', { key: i, className: 'tag-chip' }, tag);
        })
      ),
      actionButtons('episode')
    );
  }

  // Text sub-node (ego, inner_voice, memory, dna, body)
  if (info.subType === 'text') {
    var rawText = detail.raw_text || detail.text || detail.content || JSON.stringify(detail, null, 2);
    var isMonospace = (info.label && (info.label.indexOf('dna') !== -1 || info.label.indexOf('memory') !== -1 || info.label.indexOf('DNA') !== -1));
    return React.createElement('div', { style: { marginTop: 8 } },
      React.createElement('div', { className: 'detail-text-area', style: { maxHeight: 300, fontFamily: isMonospace ? 'monospace' : 'inherit' } }, rawText),
      actionButtons('text')
    );
  }

  // Experience sub-node
  if (info.subType === 'experience') {
    return React.createElement('div', { style: { marginTop: 8 } },
      detail.skill && React.createElement('div', { style: { fontSize: 10, color: T.text, fontWeight: 600 } }, detail.skill),
      detail.task && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } }, 'Task: ', detail.task),
      detail.learnings && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 4, lineHeight: 1.4 } }, 'Learnings: ', detail.learnings),
      detail.confidence != null && gaugeBar(detail.confidence, '#60a5fa', 'Confidence'),
      actionButtons('experience')
    );
  }

  // Survive / thrive sub-node
  if (info.subType === 'survive' || info.subType === 'thrive') {
    var sVal = detail.value != null ? detail.value : 0;
    return React.createElement('div', { style: { marginTop: 8 } },
      React.createElement('div', { style: { color: info.hex, fontSize: 20, fontWeight: 700 } }, (sVal * 100).toFixed(0) + '%'),
      gaugeBar(sVal, info.hex || '#94a3b8', null),
      detail.description && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 4 } }, detail.description),
      actionButtons(info.subType)
    );
  }

  // Cue index sub-node
  if (info.subType === 'cue_index') {
    return React.createElement('div', { style: { marginTop: 8 } },
      React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 } },
        React.createElement('div', { style: { textAlign: 'center' } },
          React.createElement('div', { style: { color: T.accent, fontSize: 16, fontWeight: 700 } }, detail.word_count || 0),
          React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, 'Woerter')
        ),
        React.createElement('div', { style: { textAlign: 'center' } },
          React.createElement('div', { style: { color: '#4ade80', fontSize: 16, fontWeight: 700 } }, detail.emotion_count || 0),
          React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, 'Emotionen')
        ),
        React.createElement('div', { style: { textAlign: 'center' } },
          React.createElement('div', { style: { color: '#fb923c', fontSize: 16, fontWeight: 700 } }, detail.partner_count || 0),
          React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, 'Partner')
        ),
        React.createElement('div', { style: { textAlign: 'center' } },
          React.createElement('div', { style: { color: '#a78bfa', fontSize: 16, fontWeight: 700 } }, detail.faden_count || 0),
          React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, 'Faeden')
        )
      ),
      actionButtons('cue_index')
    );
  }

  // Routing / decision sub-node
  if (info.subType === 'routing' || info.subType === 'decision') {
    var entries = Object.entries(detail);
    return React.createElement('div', { style: { marginTop: 8 } },
      entries.map(function(pair) {
        return React.createElement('div', { key: pair[0], style: { display: 'flex', justifyContent: 'space-between', fontSize: 9, padding: '2px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' } },
          React.createElement('span', { style: { color: T.textDim } }, pair[0]),
          React.createElement('span', { style: { color: T.textMid, maxWidth: '60%', textAlign: 'right', wordBreak: 'break-word' } },
            typeof pair[1] === 'object' ? JSON.stringify(pair[1]) : String(pair[1]))
        );
      }),
      actionButtons(info.subType)
    );
  }

  // Skill sub-node
  if (info.subType === 'skill') {
    return React.createElement('div', { style: { marginTop: 8 } },
      detail.level != null && React.createElement('div', { style: { fontSize: 10, color: T.text } }, 'Level: ', detail.level),
      detail.freshness != null && gaugeBar(detail.freshness, '#2dd4bf', 'Freshness'),
      detail.last_used && React.createElement('div', { style: { fontSize: 9, color: T.textDim, marginTop: 4 } }, 'Zuletzt: ', detail.last_used),
      detail.practice_points != null && React.createElement('div', { style: { fontSize: 9, color: T.textDim, marginTop: 2 } }, 'Praxis-Punkte: ', detail.practice_points),
      actionButtons('skill')
    );
  }

  // Diary sub-node
  if (info.subType === 'diary') {
    var diaryEntries = detail.entries || (Array.isArray(detail) ? detail : [detail]);
    return React.createElement('div', { style: { marginTop: 8 } },
      React.createElement('div', { className: 'obs-scroll', style: { maxHeight: 300 } },
        diaryEntries.map(function(entry, i) {
          return React.createElement('div', { key: i, style: { marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid rgba(90,110,170,0.1)' } },
            entry.date && React.createElement('div', { style: { fontSize: 8, color: T.textDim } }, entry.date),
            React.createElement('div', { style: { fontSize: 9, color: T.textMid, lineHeight: 1.4, marginTop: 2 } }, entry.text || entry.content || JSON.stringify(entry)),
            entry.emotions && React.createElement('div', { style: { marginTop: 3, display: 'flex', flexWrap: 'wrap', gap: 3 } },
              (Array.isArray(entry.emotions) ? entry.emotions : Object.keys(entry.emotions)).map(function(em, ei) {
                return React.createElement('span', { key: ei, className: 'tag-chip' }, em);
              })
            )
          );
        })
      ),
      actionButtons('diary')
    );
  }

  // Unknown type: show JSON
  return React.createElement('div', { style: { marginTop: 8 } },
    React.createElement('pre', { className: 'detail-text-area', style: { fontFamily: 'monospace', fontSize: 9 } },
      JSON.stringify(detail, null, 2)),
    actionButtons(info.subType || 'unknown')
  );
}

// ============================================================
// MAIN COMPONENT
// ============================================================
function EgonNeuroMap() {
  var mountRef = useRef(null);
  var sceneRef = useRef({});
  var dataRef = useRef(null);
  var impSys = useRef(new ThreadImpulseSystem());
  var connectedRef = useRef({ nodeIds: new Set(), threadIndices: [] });
  var clock = useRef(new THREE.Clock());
  var frame = useRef(0);
  var isDrag = useRef(false);
  var prevM = useRef({ x: 0, y: 0 });
  var rot = useRef({ x: 0.15, y: -0.3 });
  var tgtRot = useRef({ x: 0.15, y: -0.3 });
  var rc = useRef(new THREE.Raycaster());
  var mv = useRef(new THREE.Vector2());

  // Camera system refs — default overview position: (0, 0.3, 7)
  var camTarget = useRef({ pos: new THREE.Vector3(0, 0.3, 7), lookAt: new THREE.Vector3(0, 0, 0) });
  var camCurrent = useRef({ pos: new THREE.Vector3(0, 0.3, 7), lookAt: new THREE.Vector3(0, 0, 0) });
  var zoomDist = useRef(7);

  var urlParams = new URLSearchParams(window.location.search);
  var initialEgon = urlParams.get('egon') || 'adam_001';

  var egonIdState = useState(initialEgon);
  var egonId = egonIdState[0]; var setEgonId = egonIdState[1];
  var egonListState = useState([]);
  var egonList = egonListState[0]; var setEgonList = egonListState[1];
  var modeState = useState("dark");
  var mode = modeState[0]; var setMode = modeState[1];
  var loadingState = useState(true);
  var loading = loadingState[0]; var setLoading = loadingState[1];
  var hovState = useState(null);
  var hov = hovState[0]; var setHov = hovState[1];
  var selState = useState(null);
  var sel = selState[0]; var setSel = selState[1];
  var selThreadState = useState(null);
  var selThread = selThreadState[0]; var setSelThread = selThreadState[1];
  var infoState = useState(null);
  var info = infoState[0]; var setInfo = infoState[1];
  var apiDataState = useState(null);
  var apiData = apiDataState[0]; var setApiData = apiDataState[1];
  var sceneDataState = useState(null);
  var sceneData = sceneDataState[0]; var setSceneData = sceneDataState[1];

  // Navigation state
  var viewLevelState = useState('overview');
  var viewLevel = viewLevelState[0]; var setViewLevel = viewLevelState[1];
  var currentRegionState = useState(null);
  var currentRegion = currentRegionState[0]; var setCurrentRegion = currentRegionState[1];
  var regionDataState = useState(null);
  var regionData = regionDataState[0]; var setRegionData = regionDataState[1];
  var breadcrumbState = useState([]);
  var breadcrumb = breadcrumbState[0]; var setBreadcrumb = breadcrumbState[1];

  // Search state
  var searchQueryState = useState('');
  var searchQuery = searchQueryState[0]; var setSearchQuery = searchQueryState[1];
  var searchResultsState = useState(null);
  var searchResults = searchResultsState[0]; var setSearchResults = searchResultsState[1];
  var searchOpenState = useState(false);
  var searchOpen = searchOpenState[0]; var setSearchOpen = searchOpenState[1];
  var hoveredResultState = useState(null);
  var hoveredResult = hoveredResultState[0]; var setHoveredResult = hoveredResultState[1];
  var searchTimerRef = useRef(null);

  // Formation path label state (for overlay)
  var formationLabelState = useState(null);
  var formationLabel = formationLabelState[0]; var setFormationLabel = formationLabelState[1];
  var formationColorState = useState(null);
  var formationColor = formationColorState[0]; var setFormationColor = formationColorState[1];

  var T = THEMES[mode];

  // ---------- Fire a formation path ----------
  var fireFormation = useCallback(function(pathDef) {
    var sc = sceneRef.current;
    if (!sc.threadLines || !dataRef.current) return;
    impSys.current.fireFormationPath(pathDef, dataRef.current, sc.threadLines);
    setFormationLabel(pathDef.label);
    setFormationColor(pathDef.color);
    // Auto-clear label after path duration + 3s
    setTimeout(function() {
      setFormationLabel(null);
      setFormationColor(null);
    }, (pathDef.path.length * 300) + 3000);
  }, []);

  // ---------- Zoom to a specific node ----------
  var zoomToNode = useCallback(function(nodeInfo) {
    if (!nodeInfo) return;
    var wp = nodeInfo.worldPos || nodeInfo.pos;
    if (!wp) return;
    var px, py, pz;
    if (Array.isArray(wp)) { px = wp[0]; py = wp[1]; pz = wp[2]; }
    else { px = wp.x; py = wp.y; pz = wp.z; }
    camTarget.current.pos.set(px + 0.5, py + 0.3, pz + 2.0);
    camTarget.current.lookAt.set(px, py, pz);
  }, []);

  // ---------- navigateTo: central navigation function ----------
  // v7: NO auto-zoom. Camera is ONLY changed by explicit user action (zoom button or mouse wheel).
  var navigateTo = useCallback(function(level, opts) {
    opts = opts || {};
    var sc = sceneRef.current;
    if (!sc.pivot) return;

    if (level === 'overview') {
      // Remove all sub-node meshes
      if (sc.subNodeMeshes) {
        sc.subNodeMeshes.forEach(function(m) {
          if (m.geometry) m.geometry.dispose();
          if (m.material) m.material.dispose();
          sc.pivot.remove(m);
        });
        sc.subNodeMeshes = [];
      }
      // Restore region opacities
      if (sc.meshes && dataRef.current) {
        sc.meshes.forEach(function(m, i) {
          var node = dataRef.current.allNodes[i];
          if (!node) return;
          m.material.opacity = node.type === 'region' ? T.regionOp : 0.85;
          m.visible = true;
        });
      }
      // Restore threads
      if (sc.threadLines) {
        sc.threadLines.forEach(function(tl) {
          tl.line.visible = true;
        });
      }
      // NO camera change — user controls zoom themselves
      setViewLevel('overview');
      setCurrentRegion(null);
      setRegionData(null);
      setBreadcrumb([]);
      setSel(null);
      setSelThread(null);
      setInfo(null);
      connectedRef.current = { nodeIds: new Set(), threadIndices: [] };
    }
    else if (level === 'region') {
      setViewLevel('region');
      if (opts.regionKey && opts.regionLabel) {
        setBreadcrumb([{ level: 'overview', label: '\u00DCbersicht' }, { level: 'region', label: opts.regionLabel, regionKey: opts.regionKey }]);
      }
      // NO camera change
      setInfo(opts.info || null);
    }
    else if (level === 'item') {
      setViewLevel('item');
      if (opts.subNode) {
        setInfo(opts.subNode);
        // NO camera change — user clicks "Hierher zoomen" for that
      }
      if (breadcrumb.length >= 2) {
        setBreadcrumb(function(prev) {
          var next = prev.slice(0, 2);
          next.push({ level: 'item', label: (opts.subNode && opts.subNode.label) ? opts.subNode.label : 'Detail' });
          return next;
        });
      }
    }
  }, [T, breadcrumb]);

  // ---------- Escape key handler ----------
  useEffect(function() {
    function onKey(e) {
      if (e.key === 'Escape') {
        if (searchOpen) {
          setSearchOpen(false);
          setSearchQuery('');
          setSearchResults(null);
          setHoveredResult(null);
        } else if (viewLevel === 'item') {
          navigateTo('region', { regionKey: currentRegion, regionLabel: REGIONS[currentRegion] ? REGIONS[currentRegion].label : currentRegion, info: null });
        } else if (viewLevel === 'region') {
          navigateTo('overview');
        }
      }
    }
    window.addEventListener('keydown', onKey);
    return function() { window.removeEventListener('keydown', onKey); };
  }, [viewLevel, currentRegion, navigateTo, searchOpen]);

  // ---------- Search with debounce (300ms) ----------
  useEffect(function() {
    if (!searchQuery || searchQuery.length < 2) { setSearchResults(null); return; }
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(function() {
      window.NeuroMapAPI.searchBrain(egonId, searchQuery).then(function(data) {
        if (data) setSearchResults(data.results || []);
      });
    }, 300);
  }, [searchQuery, egonId]);

  // Load EGON list
  useEffect(function() {
    window.NeuroMapAPI.fetchEgonList().then(function(list) {
      if (list && list.length > 0) setEgonList(list);
    });
  }, []);

  // Load brain data
  useEffect(function() {
    var cancelled = false;
    setLoading(true);
    setSel(null); setSelThread(null); setInfo(null);
    setViewLevel('overview'); setCurrentRegion(null); setRegionData(null); setBreadcrumb([]);
    setSearchQuery(''); setSearchResults(null); setSearchOpen(false); setHoveredResult(null);

    var url = new URL(window.location);
    url.searchParams.set('egon', egonId);
    window.history.replaceState({}, '', url);

    window.NeuroMapAPI.loadFullBrain(egonId).then(function(data) {
      if (cancelled) return;
      setApiData(data);
      setSceneData(buildSceneData(data));
      setLoading(false);
    });
    return function() { cancelled = true; };
  }, [egonId]);

  // Live-Event-Polling
  useEffect(function() {
    var lastEventTs = Date.now();
    var pollTimer = setInterval(function() {
      window.NeuroMapAPI.fetchEvents(egonId, lastEventTs).then(function(events) {
        if (!events || !events.events || !events.events.length) return;
        lastEventTs = Date.now();

        var sc = sceneRef.current;

        events.events.forEach(function(ev) {
          if (ev.typ === 'BOND_NEU' && sc.threadLines) {
            var sp = FORMATION_PATHS.bond;
            impSys.current.firePath(sp.path, sp.color, 0.6, dataRef.current, sc.threadLines);
          }
          if (ev.typ === 'STRUKTUR_UPDATE' && sc.threadLines) {
            var sp2 = FORMATION_PATHS.emotion;
            impSys.current.firePath(sp2.path, sp2.color, 0.8, dataRef.current, sc.threadLines);
          }
        });

        var structural = events.events.some(function(e) {
          return e.typ === 'BOND_NEU' || e.typ === 'BOND_UPDATE' ||
            e.typ === 'FADEN_NEU' || e.typ === 'STRUKTUR_UPDATE';
        });

        if (structural) {
          console.log('[NeuroMap] Struktur-Event erkannt, lade Gehirn neu...');
          window.NeuroMapAPI.loadFullBrain(egonId).then(function(data) {
            setApiData(data);
            setSceneData(buildSceneData(data));
          });
        }
      }).catch(function() { /* Stille Fehler beim Polling */ });
    }, 5000);

    return function() { clearInterval(pollTimer); };
  }, [egonId]);

  // THREE.js Setup
  useEffect(function() {
    if (!mountRef.current || !sceneData) return;
    var el = mountRef.current;

    // Cleanup
    if (sceneRef.current.renderer) {
      cancelAnimationFrame(frame.current);
      if (sceneRef.current.impTimer) clearInterval(sceneRef.current.impTimer);
      if (sceneRef.current.renderer.domElement && sceneRef.current.renderer.domElement.parentNode === el)
        el.removeChild(sceneRef.current.renderer.domElement);
      sceneRef.current.renderer.dispose();
    }

    var w = el.clientWidth, h = el.clientHeight;
    var scene = new THREE.Scene();
    scene.background = new THREE.Color(T.bg);
    scene.fog = new THREE.FogExp2(T.fog, T.fogDensity);

    var camera = new THREE.PerspectiveCamera(48, w / h, 0.1, 100);
    camera.position.set(0, 0.3, 7);

    // Init camera system
    camTarget.current.pos.set(0, 0.3, 7);
    camTarget.current.lookAt.set(0, 0, 0);
    camCurrent.current.pos.set(0, 0.3, 7);
    camCurrent.current.lookAt.set(0, 0, 0);
    zoomDist.current = 7;

    var renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight('#2a2f45', 0.5));
    var dLight = new THREE.DirectionalLight("#e0e4f0", 0.35);
    dLight.position.set(4, 6, 5);
    scene.add(dLight);

    var pivot = new THREE.Group();
    scene.add(pivot);
    dataRef.current = sceneData;

    // --- BRAIN SHELL (translucent ellipsoid) ---
    var brainGeo = new THREE.SphereGeometry(1, 32, 24);
    var brainMat = new THREE.MeshPhongMaterial({
      color: '#2a3050', transparent: true, opacity: 0.04,
      side: THREE.BackSide, depthWrite: false, shininess: 20,
    });
    var brainShell = new THREE.Mesh(brainGeo, brainMat);
    brainShell.scale.set(2.2, 2.0, 2.4);
    brainShell.position.set(0, 0.1, 0);
    brainShell.renderOrder = -1;
    pivot.add(brainShell);

    // Wireframe overlay
    var wireGeo = new THREE.SphereGeometry(1, 16, 12);
    var wireMat = new THREE.MeshBasicMaterial({
      color: '#3a4570', wireframe: true, transparent: true, opacity: 0.03,
    });
    var wireShell = new THREE.Mesh(wireGeo, wireMat);
    wireShell.scale.set(2.25, 2.05, 2.45);
    wireShell.position.set(0, 0.1, 0);
    wireShell.renderOrder = -2;
    pivot.add(wireShell);

    // --- REGION NODES (grosse leuchtende Kugeln) ---
    var sGeo = new THREE.SphereGeometry(1, 20, 20);
    var meshes = [];

    for (var ri = 0; ri < sceneData.regionNodes.length; ri++) {
      var rn = sceneData.regionNodes[ri];
      var mat = new THREE.MeshPhongMaterial({
        color: rn.hex, emissive: rn.hex,
        emissiveIntensity: T.regionGlow + rn.intensity * 0.4,
        transparent: true, opacity: T.regionOp, shininess: 60,
      });
      var m = new THREE.Mesh(sGeo, mat);
      m.position.set(rn.pos[0], rn.pos[1], rn.pos[2]);
      m.scale.setScalar(rn.size);
      m.userData = { nodeId: rn.id, type: 'region', regionKey: rn.region };
      pivot.add(m);
      meshes.push(m);
    }

    // --- BOND NODES (kleinere Kugeln, Groesse = Score) ---
    for (var bi = 0; bi < sceneData.bondNodes.length; bi++) {
      var bn = sceneData.bondNodes[bi];
      var bmat = new THREE.MeshPhongMaterial({
        color: bn.hex, emissive: bn.hex,
        emissiveIntensity: 0.5 + bn.staerke * 0.4,
        transparent: true, opacity: 0.85, shininess: 40,
      });
      var bm = new THREE.Mesh(sGeo, bmat);
      bm.position.set(bn.pos[0], bn.pos[1], bn.pos[2]);
      bm.scale.setScalar(bn.size);
      bm.userData = { nodeId: bn.id, type: 'bond' };
      pivot.add(bm);
      meshes.push(bm);

      // Bezier connection Bond -> Amygdala
      var amyPos = REGIONS.amygdala ? REGIONS.amygdala.pos : [0, 0, 0];
      var bondStart = new THREE.Vector3(bn.pos[0], bn.pos[1], bn.pos[2]);
      var bondEnd = new THREE.Vector3(amyPos[0], amyPos[1], amyPos[2]);
      var bondMid = new THREE.Vector3(
        (bondStart.x + bondEnd.x) * 0.5 * 0.7,
        (bondStart.y + bondEnd.y) * 0.5 + 0.3,
        (bondStart.z + bondEnd.z) * 0.5 * 0.7
      );
      var bondCurve = new THREE.QuadraticBezierCurve3(bondStart, bondMid, bondEnd);
      var bondCurvePoints = bondCurve.getPoints(20);
      var bondLineGeo = new THREE.BufferGeometry().setFromPoints(bondCurvePoints);
      var bondLineMat = new THREE.LineBasicMaterial({
        color: bn.hex, transparent: true, opacity: 0.1 + bn.staerke * 0.3,
      });
      pivot.add(new THREE.Line(bondLineGeo, bondLineMat));
    }

    // --- DRIVE NODES (kleine leuchtende Punkte) ---
    for (var di = 0; di < sceneData.driveNodes.length; di++) {
      var dn = sceneData.driveNodes[di];
      var dmat = new THREE.MeshPhongMaterial({
        color: dn.hex, emissive: dn.hex,
        emissiveIntensity: 0.6,
        transparent: true, opacity: 0.9, shininess: 80,
      });
      var dm = new THREE.Mesh(sGeo, dmat);
      dm.position.set(dn.pos[0], dn.pos[1], dn.pos[2]);
      dm.scale.setScalar(dn.size);
      dm.userData = { nodeId: dn.id, type: 'drive' };
      pivot.add(dm);
      meshes.push(dm);
    }

    // --- FAEDEN (Bezier-Kurven statt gerader Linien) ---
    var threadLines = [];
    for (var ti = 0; ti < sceneData.threads.length; ti++) {
      var t_data = sceneData.threads[ti];
      var vonNode = sceneData.regionNodes[t_data.vonIdx];
      var nachNode = sceneData.regionNodes[t_data.nachIdx];
      if (!vonNode || !nachNode) continue;

      var p1 = new THREE.Vector3(vonNode.pos[0], vonNode.pos[1], vonNode.pos[2]);
      var p2 = new THREE.Vector3(nachNode.pos[0], nachNode.pos[1], nachNode.pos[2]);
      // Control point: midpoint pulled toward brain center + Y bulge
      var midX = (p1.x + p2.x) * 0.5;
      var midY = (p1.y + p2.y) * 0.5;
      var midZ = (p1.z + p2.z) * 0.5;
      var pullFactor = 0.3;
      var controlPoint = new THREE.Vector3(
        midX * (1.0 - pullFactor),
        midY * (1.0 - pullFactor) + 0.25,
        midZ * (1.0 - pullFactor)
      );

      var bezierCurve = new THREE.QuadraticBezierCurve3(p1, controlPoint, p2);
      var curvePoints = bezierCurve.getPoints(20);
      var tgeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      var baseOp = Math.max(0.05, t_data.opacity * 0.8);
      var tmat = new THREE.LineBasicMaterial({
        color: t_data.farbe, transparent: true, opacity: baseOp,
      });
      var tline = new THREE.Line(tgeo, tmat);
      tline.userData = { threadIdx: threadLines.length, dicke: t_data.dicke };
      pivot.add(tline);
      threadLines.push({ line: tline, thread: t_data, baseOp: baseOp });

      // Dicke Faeden bekommen ein zweites paralleles Line-Paar fuer visuellen "Dicke"-Effekt
      if (t_data.dicke > 0.4) {
        var offset = 0.03 * t_data.dicke;
        var dirs = [[offset, 0, 0], [0, offset, 0]];
        for (var dd = 0; dd < dirs.length; dd++) {
          var dir = dirs[dd];
          var offsetP1 = new THREE.Vector3(p1.x + dir[0], p1.y + dir[1], p1.z + dir[2]);
          var offsetP2 = new THREE.Vector3(p2.x + dir[0], p2.y + dir[1], p2.z + dir[2]);
          var offsetCtrl = new THREE.Vector3(controlPoint.x + dir[0], controlPoint.y + dir[1], controlPoint.z + dir[2]);
          var offCurve = new THREE.QuadraticBezierCurve3(offsetP1, offsetCtrl, offsetP2);
          var offPoints = offCurve.getPoints(20);
          var g2 = new THREE.BufferGeometry().setFromPoints(offPoints);
          var m2 = new THREE.LineBasicMaterial({
            color: t_data.farbe, transparent: true, opacity: baseOp * 0.5,
          });
          pivot.add(new THREE.Line(g2, m2));
        }
      }
    }

    // --- Subtle region-internal connections ---
    for (var rhi = 0; rhi < sceneData.regionNodes.length; rhi++) {
      var rnHalo = sceneData.regionNodes[rhi];
      if (rnHalo.intensity > 0.1) {
        var ringGeo = new THREE.RingGeometry(rnHalo.size * 1.2, rnHalo.size * 1.5, 24);
        var ringMat = new THREE.MeshBasicMaterial({
          color: rnHalo.hex, transparent: true, opacity: rnHalo.intensity * 0.15,
          side: THREE.DoubleSide,
        });
        var ring = new THREE.Mesh(ringGeo, ringMat);
        ring.position.set(rnHalo.pos[0], rnHalo.pos[1], rnHalo.pos[2]);
        ring.lookAt(camera.position);
        pivot.add(ring);
      }
    }

    sceneRef.current = { scene: scene, camera: camera, renderer: renderer, pivot: pivot, meshes: meshes, threadLines: threadLines, subNodeMeshes: [] };

    // Impulse timer — sanftes "Lebenszeichen" alle 3 Sekunden auf dem dicksten Faden
    var impTimer = setInterval(function() {
      if (threadLines.length === 0) return;
      var maxIdx = 0, maxDicke = 0;
      threadLines.forEach(function(tl, i) {
        if (tl.thread.dicke > maxDicke) { maxDicke = tl.thread.dicke; maxIdx = i; }
      });
      impSys.current.fire(maxIdx, threadLines[maxIdx].thread.farbe, 0.5);
    }, 3000);
    sceneRef.current.impTimer = impTimer;

    // Animate
    var animate = function() {
      frame.current = requestAnimationFrame(animate);
      var dt = Math.min(clock.current.getDelta(), 0.05);
      var t = clock.current.getElapsedTime();

      // Rotation (existing drag logic)
      rot.current.x += (tgtRot.current.x - rot.current.x) * 0.05;
      rot.current.y += (tgtRot.current.y - rot.current.y) * 0.05;
      pivot.rotation.x = rot.current.x;
      pivot.rotation.y = rot.current.y;
      if (!isDrag.current) tgtRot.current.y += 0.0004;

      // Camera lerp system
      var lerpFactor = 0.04;
      camCurrent.current.pos.lerp(camTarget.current.pos, lerpFactor);
      camCurrent.current.lookAt.lerp(camTarget.current.lookAt, lerpFactor);
      camera.position.copy(camCurrent.current.pos);
      camera.lookAt(camCurrent.current.lookAt);

      impSys.current.update(dt);

      // Connected-Set fuer diesen Frame
      var cRef = connectedRef.current;
      var hasSelection = sel !== null;
      var connectedThreads = new Set(cRef.threadIndices);

      // Search highlight: check if any result matches a region
      var searchHighlightRegion = hoveredResult ? hoveredResult.region : null;
      var searchResultRegions = {};
      if (searchResults && searchResults.length > 0) {
        for (var sri = 0; sri < searchResults.length; sri++) {
          if (searchResults[sri].region) {
            searchResultRegions[searchResults[sri].region] = true;
          }
        }
      }

      // Thread glow — grey synapses by default, impulse-active show real color
      var dimOpVal = T.dimOp;
      threadLines.forEach(function(tl, i) {
        var glow = impSys.current.getGlow(i);
        var isSelected = selThread === i;
        var isConnected = hasSelection && connectedThreads.has(i);

        if (isSelected) {
          tl.line.material.color.set(tl.thread.farbe);
          tl.line.material.opacity = 0.6 + Math.sin(t * 2) * 0.1;
        } else if (isConnected) {
          tl.line.material.color.set(tl.thread.farbe);
          tl.line.material.opacity = Math.max(tl.baseOp * 1.5, 0.4 + Math.sin(t * 1.5) * 0.1, glow * T.threadFlash);
        } else if (glow > 0.01) {
          tl.line.material.color.set(tl.thread.farbe);
          tl.line.material.opacity = Math.max(dimOpVal + tl.thread.dicke * 0.15, glow * T.threadFlash);
        } else if (hasSelection) {
          tl.line.material.color.set('#3a3f50');
          tl.line.material.opacity = tl.baseOp * 0.15;
        } else {
          tl.line.material.color.set('#3a3f50');
          tl.line.material.opacity = dimOpVal + tl.thread.dicke * 0.15;
        }
      });

      // Node breathe + selection + connected-highlighting + formation path + search highlight
      meshes.forEach(function(m, i) {
        var node = sceneData.allNodes[i];
        if (!node) return;
        var isHov = hov === node.id;
        var isSel = sel === node.id;
        var isConnected = hasSelection && cRef.nodeIds.has(node.id);
        var base = node.size || 0.1;
        var breathe = Math.sin(t * 1.5 + i * 1.2) * 0.003;

        // Formation path highlighting
        var inFormation = node.type === 'region' && impSys.current.isRegionInFormationPath(node.region);
        var fColor = impSys.current.getFormationColor();

        // Search highlighting
        var isSearchHighlight = node.type === 'region' && node.region === searchHighlightRegion;
        var isSearchResultRegion = node.type === 'region' && searchResultRegions[node.region];

        if (inFormation) {
          // Formation path: bright glow with pulse, scale 1.3x
          m.scale.setScalar(base * 1.3 + Math.sin(t * 4) * 0.008);
          if (fColor) m.material.emissive.set(fColor);
          m.material.emissiveIntensity = 0.8 + Math.sin(t * 4) * 0.2;
          m.material.opacity = 1;
        } else if (isSel) {
          m.scale.setScalar(base * 1.6 + Math.sin(t * 3) * 0.008);
          m.material.emissive.set(node.hex);
          m.material.emissiveIntensity = 0.9;
          m.material.opacity = 1;
        } else if (isConnected) {
          m.scale.setScalar(base * 1.2 + Math.sin(t * 2 + i) * 0.005);
          m.material.emissive.set(node.hex);
          m.material.emissiveIntensity = 0.7;
          m.material.opacity = 0.95;
        } else if (isSearchHighlight) {
          // Search hover: bright glow + scale pulse
          m.scale.setScalar(base * 1.4 + Math.sin(t * 5) * 0.01);
          m.material.emissive.set(node.hex);
          m.material.emissiveIntensity = 0.9;
          m.material.opacity = 1;
        } else if (isSearchResultRegion) {
          // All matching regions from search results: dim glow
          m.scale.setScalar(base * 1.1);
          m.material.emissive.set(node.hex);
          m.material.emissiveIntensity = 0.6;
          m.material.opacity = 0.9;
        } else if (isHov) {
          m.scale.setScalar(base * 1.3);
          m.material.emissive.set(node.hex);
          m.material.emissiveIntensity = 0.7;
          m.material.opacity = 1;
        } else {
          m.scale.setScalar(base + breathe);
          m.material.emissive.set(node.hex);
          m.material.emissiveIntensity = node.type === 'region'
            ? T.regionGlow + (node.intensity || 0) * 0.3
            : 0.5;
          m.material.opacity = hasSelection ? T.dimOp + 0.08 : T.regionOp;
        }
      });

      // Sub-node meshes breathe
      if (sceneRef.current.subNodeMeshes) {
        sceneRef.current.subNodeMeshes.forEach(function(sm, si) {
          var sBreath = Math.sin(t * 2 + si * 0.8) * 0.003;
          var baseSize = sm.userData.baseSize || 0.08;
          sm.scale.setScalar(baseSize + sBreath);
        });
      }

      renderer.render(scene, camera);
    };
    animate();

    // Mouse wheel handler for zoom — this is the ONLY way to zoom
    var onWheel = function(e) {
      e.preventDefault();
      var delta = e.deltaY > 0 ? 0.5 : -0.5;
      zoomDist.current = Math.max(1.5, Math.min(12, zoomDist.current + delta));

      // Calculate zoom direction from current camera
      var dir = new THREE.Vector3();
      dir.subVectors(camTarget.current.lookAt, camCurrent.current.pos).normalize();
      var newPos = new THREE.Vector3().copy(camTarget.current.lookAt).sub(dir.multiplyScalar(zoomDist.current));
      camTarget.current.pos.copy(newPos);
    };
    el.addEventListener('wheel', onWheel, { passive: false });

    var onResize = function() {
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(el.clientWidth, el.clientHeight);
    };
    window.addEventListener("resize", onResize);

    return function() {
      clearInterval(impTimer);
      cancelAnimationFrame(frame.current);
      window.removeEventListener("resize", onResize);
      el.removeEventListener('wheel', onWheel);
      if (el && renderer.domElement && renderer.domElement.parentNode === el) el.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, [sceneData]);

  // Theme
  useEffect(function() {
    var s = sceneRef.current;
    if (!s.scene) return;
    s.scene.background.set(T.bg);
    if (s.scene.fog) s.scene.fog.color.set(T.fog);
  }, [mode]);

  // Mouse
  var getHit = useCallback(function(e) {
    if (!mountRef.current || !sceneRef.current.camera) return null;
    var r = mountRef.current.getBoundingClientRect();
    mv.current.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    mv.current.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    rc.current.setFromCamera(mv.current, sceneRef.current.camera);
    var allTargets = (sceneRef.current.subNodeMeshes || []).concat(sceneRef.current.meshes || []);
    var h = rc.current.intersectObjects(allTargets);
    return h.length > 0 ? h[0].object : null;
  }, []);

  var onDown = useCallback(function(e) {
    isDrag.current = false;
    prevM.current = { x: e.clientX, y: e.clientY };
  }, []);

  var onMove = useCallback(function(e) {
    if (e.buttons === 1) {
      var dx = e.clientX - prevM.current.x, dy = e.clientY - prevM.current.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) isDrag.current = true;
      tgtRot.current.y += dx * 0.005;
      tgtRot.current.x += dy * 0.005;
      prevM.current = { x: e.clientX, y: e.clientY };
    } else {
      var hitObj = getHit(e);
      if (hitObj && hitObj.userData) {
        setHov(hitObj.userData.nodeId != null ? hitObj.userData.nodeId : null);
      } else {
        setHov(null);
      }
    }
  }, [getHit]);

  // Finde alle verbundenen Knoten + Faeden fuer einen Knoten
  var getConnected = useCallback(function(nodeId) {
    if (!sceneData) return { threadIndices: [], nodeIds: new Set() };
    var threadIndices = [];
    var nodeIds = new Set();
    nodeIds.add(nodeId);

    sceneData.threads.forEach(function(t, i) {
      if (t.von === nodeId || t.nach === nodeId) {
        threadIndices.push(i);
        nodeIds.add(t.von);
        nodeIds.add(t.nach);
      }
    });

    (sceneData.bondNodes || []).forEach(function(bn) {
      if (bn.region === nodeId || bn.id === nodeId) {
        nodeIds.add(bn.id);
      }
    });

    (sceneData.driveNodes || []).forEach(function(dn) {
      if (dn.region === nodeId || dn.id === nodeId) {
        nodeIds.add(dn.id);
      }
    });

    return { threadIndices: threadIndices, nodeIds: nodeIds };
  }, [sceneData]);

  // ---------- Deep dive into a region (Level 2) ----------
  var deepDiveRegion = useCallback(function(regionKey) {
    if (!sceneRef.current.pivot || !sceneData) return;
    var regDef = REGIONS[regionKey];
    if (!regDef) return;
    var sc = sceneRef.current;

    setCurrentRegion(regionKey);
    setViewLevel('region');
    setBreadcrumb([
      { level: 'overview', label: '\u00DCbersicht' },
      { level: 'region', label: regDef.label, regionKey: regionKey },
    ]);

    // NO camera change — user zooms with "Hierher zoomen" button only

    // Fade all other region nodes to opacity 0.05
    sc.meshes.forEach(function(m, i) {
      var node = dataRef.current ? dataRef.current.allNodes[i] : null;
      if (!node) return;
      if (node.type === 'region' && node.region === regionKey) {
        m.material.opacity = T.regionOp;
      } else {
        m.material.opacity = 0.05;
      }
    });

    // Fetch region detail from API
    window.NeuroMapAPI.fetchRegionDetail(egonId, regionKey).then(function(data) {
      if (!data) return;
      setRegionData(data);

      // Remove old sub-node meshes
      if (sc.subNodeMeshes) {
        sc.subNodeMeshes.forEach(function(old) {
          if (old.geometry) old.geometry.dispose();
          if (old.material) old.material.dispose();
          sc.pivot.remove(old);
        });
      }
      sc.subNodeMeshes = [];

      var rPos = regDef.pos;

      // Create sub-node meshes from API data
      var subNodes = data.sub_nodes || data.nodes || data.items || [];
      if (subNodes.length === 0) return;

      var count = subNodes.length;
      var radius = 0.6 + count * 0.04;
      var subGeo = new THREE.SphereGeometry(1, 16, 16);

      subNodes.forEach(function(sn, idx) {
        var angle = (idx / count) * Math.PI * 2;
        var sx = rPos[0] + Math.cos(angle) * radius;
        var sy = rPos[1] + Math.sin(angle) * radius * 0.5;
        var sz = rPos[2] + Math.sin(angle) * 0.3;

        var snSize = sn.size || 0.08;
        var snColor = sn.hex || sn.color || regDef.hex;
        var snMat = new THREE.MeshPhongMaterial({
          color: snColor, emissive: snColor,
          emissiveIntensity: 0.5,
          transparent: true, opacity: 0.85, shininess: 50,
        });
        var snMesh = new THREE.Mesh(subGeo, snMat);
        snMesh.position.set(sx, sy, sz);
        snMesh.scale.setScalar(snSize);
        snMesh.userData = {
          nodeId: 'sub_' + idx,
          type: 'sub_node',
          subType: sn.type || 'unknown',
          label: sn.label || sn.name || ('Sub-' + idx),
          hex: snColor,
          detail: sn.detail || sn,
          baseSize: snSize,
          worldPos: { x: sx, y: sy, z: sz },
          region: regionKey,
        };
        sc.pivot.add(snMesh);
        sc.subNodeMeshes.push(snMesh);
      });
    });
  }, [sceneData, egonId, T]);

  // ---------- Click handler ----------
  var onClick = useCallback(function(e) {
    if (isDrag.current) return;
    var hitObj = getHit(e);
    if (!hitObj || !hitObj.userData) {
      // Click on empty space: deselect
      setSel(null); setSelThread(null); setInfo(null);
      connectedRef.current = { nodeIds: new Set(), threadIndices: [] };
      return;
    }

    var ud = hitObj.userData;

    // Sub-node click (Level 2 -> Level 3)
    if (ud.type === 'sub_node') {
      var subInfo = {
        label: ud.label,
        hex: ud.hex,
        type: 'sub_node',
        subType: ud.subType,
        detail: ud.detail,
        worldPos: ud.worldPos,
        region: ud.region,
      };
      setInfo(subInfo);
      navigateTo('item', { subNode: subInfo });

      // Fire formation path for sub-node type
      var subFormation = FORMATION_PATHS[ud.subType] || FORMATION_PATHS.unknown;
      fireFormation(subFormation);
      return;
    }

    var id = ud.nodeId;
    if (id !== null && id !== sel) {
      setSel(id);
      setSelThread(null);
      var node = null;
      if (dataRef.current && dataRef.current.allNodes) {
        node = dataRef.current.allNodes.find(function(n) { return n.id === id; });
      }
      if (node) setInfo(node);

      var connected = getConnected(id);
      connectedRef.current = connected;

      var sc = sceneRef.current;
      if (sc && sc.threadLines) {
        connected.threadIndices.forEach(function(idx, delay) {
          setTimeout(function() {
            if (sc.threadLines[idx]) {
              impSys.current.fire(idx, sc.threadLines[idx].thread.farbe, 0.6);
            }
          }, delay * 80);
        });
      }

      // Fire formation path based on node type
      if (node && node.type === 'bond') {
        fireFormation(FORMATION_PATHS.bond);
      } else if (node && node.type === 'drive') {
        fireFormation(FORMATION_PATHS.drive);
      }
    } else {
      setSel(null); setSelThread(null); setInfo(null);
      connectedRef.current = { nodeIds: new Set(), threadIndices: [] };
    }
  }, [sel, getHit, getConnected, navigateTo, fireFormation]);

  // ---------- Double-click handler (Region deep dive) ----------
  var onDblClick = useCallback(function(e) {
    var hitObj = getHit(e);
    if (!hitObj || !hitObj.userData) return;
    var ud = hitObj.userData;
    if (ud.type === 'region' && ud.regionKey) {
      deepDiveRegion(ud.regionKey);
    }
  }, [getHit, deepDiveRegion]);

  // Loading
  if (loading || !sceneData) {
    return (
      React.createElement('div', { className: 'loading-screen' },
        React.createElement('div', { className: 'spinner' }),
        React.createElement('div', { className: 'label' }, 'Lade Gehirn von ' + (EGON_NAMES[egonId] || egonId) + '...')
      )
    );
  }

  var egonName = EGON_NAMES[egonId] || egonId;
  var pnl = "glass";

  // Count connections for region info
  function getRegionConnectionSummary(regionKey) {
    if (!sceneData) return { incoming: 0, outgoing: 0, connectedRegions: [] };
    var incoming = 0;
    var outgoing = 0;
    var connected = {};
    sceneData.threads.forEach(function(t) {
      if (t.von === regionKey) {
        outgoing++;
        connected[t.nach] = true;
      }
      if (t.nach === regionKey) {
        incoming++;
        connected[t.von] = true;
      }
    });
    return { incoming: incoming, outgoing: outgoing, connectedRegions: Object.keys(connected) };
  }

  return (
    React.createElement('div', { style: { width: "100%", height: "100vh",
      background: mode === 'dark'
        ? "radial-gradient(ellipse at 50% 35%, #151a28 0%, #0d1017 55%, #080a10 100%)"
        : "radial-gradient(ellipse at 50% 35%, #fafbff 0%, #eef0f6 55%, #e2e6f0 100%)",
      position: "relative", overflow: "hidden" } },

      /* TOP BAR */
      React.createElement('div', { className: 'topbar' },
        React.createElement('div', { style: { display: "flex", alignItems: "center", gap: 12 } },
          React.createElement('div', { className: 'brand' },
            React.createElement('span', { className: 'name' }, egonName.toUpperCase()),
            React.createElement('span', { className: 'sub' }, 'NEURO-MAP v7')
          ),
          React.createElement('div', { className: pnl + ' egon-selector' },
            React.createElement('select', { value: egonId, onChange: function(e) { setEgonId(e.target.value); } },
              (egonList.length > 0 ? egonList : Object.keys(EGON_NAMES)).map(function(id) {
                return React.createElement('option', { key: id, value: id }, EGON_NAMES[id] || id);
              })
            )
          )
        ),

        /* Complexity Badge */
        React.createElement('div', { className: pnl, style: { padding: '5px 14px', display: 'flex', gap: 14, fontSize: 10 } },
          React.createElement('span', { style: { color: T.textDim } }, 'Faeden: ', React.createElement('b', { style: { color: T.text } }, sceneData.stats.total || 0)),
          React.createElement('span', { style: { color: T.textDim } }, 'Bonds: ', React.createElement('b', { style: { color: '#fb923c' } }, sceneData.bondNodes.length)),
          React.createElement('span', { style: { color: T.textDim } }, 'Drives: ', React.createElement('b', { style: { color: '#facc15' } }, sceneData.driveNodes.length)),
          React.createElement('span', { style: { color: T.textDim } }, 'Komplexitaet: ', React.createElement('b', { style: { color: T.accent } }, sceneData.complexity))
        ),

        React.createElement('button', { className: pnl + ' theme-toggle',
          onClick: function() { setMode(function(m) { return m === "dark" ? "light" : "dark"; }); } },
          mode === "dark" ? "\u2600 Light" : "\u263E Dark"
        )
      ),

      /* SEARCH BAR */
      React.createElement('div', { className: pnl + ' search-bar', style: { position: 'absolute', top: 52, left: '50%', transform: 'translateX(-50%)', zIndex: 20 } },
        React.createElement('span', { style: { color: T.textDim, fontSize: 13 } }, '\uD83D\uDD0D'),
        React.createElement('input', {
          type: 'text',
          placeholder: 'Gehirn durchsuchen...',
          value: searchQuery,
          onFocus: function() { setSearchOpen(true); },
          onChange: function(e) { setSearchQuery(e.target.value); setSearchOpen(true); },
          style: { background: 'transparent', border: 'none', outline: 'none', color: T.text, fontFamily: 'inherit', fontSize: 12, flex: 1 },
        }),
        searchQuery && React.createElement('button', {
          style: { background: 'none', border: 'none', color: T.textDim, cursor: 'pointer', fontSize: 13, padding: 0 },
          onClick: function() { setSearchQuery(''); setSearchResults(null); setSearchOpen(false); setHoveredResult(null); }
        }, '\u2715'),
        /* Search results dropdown */
        searchOpen && searchResults && searchResults.length > 0 && React.createElement('div', { className: 'search-results' },
          searchResults.slice(0, 20).map(function(result, idx) {
            var regionDef = REGIONS[result.region];
            var dotColor = regionDef ? regionDef.hex : '#8890aa';
            var matchSnippet = result.match || result.snippet || result.label || '';
            if (matchSnippet.length > 80) matchSnippet = matchSnippet.slice(0, 80) + '...';
            return React.createElement('div', {
              key: idx,
              className: 'search-item',
              onMouseEnter: function() { setHoveredResult(result); },
              onMouseLeave: function() { setHoveredResult(null); },
              onClick: function() {
                setInfo({
                  label: result.label || result.type || 'Ergebnis',
                  hex: dotColor,
                  type: result.type === 'region' ? 'region' : 'sub_node',
                  subType: result.type || 'unknown',
                  detail: result.detail || result,
                  region: result.region,
                  worldPos: regionDef ? { x: regionDef.pos[0], y: regionDef.pos[1], z: regionDef.pos[2] } : null,
                });
                var pathDef = FORMATION_PATHS[result.type] || FORMATION_PATHS.unknown;
                fireFormation(pathDef);
                setSearchOpen(false);
              }
            },
              React.createElement('div', { className: 'search-dot', style: { background: dotColor } }),
              React.createElement('div', { style: { flex: 1 } },
                React.createElement('div', { className: 'search-label', style: { color: T.text } }, result.label || result.type || 'Treffer'),
                React.createElement('div', { className: 'search-match' }, matchSnippet)
              )
            );
          })
        ),
        searchOpen && searchResults && searchResults.length === 0 && searchQuery.length >= 2 && React.createElement('div', { className: 'search-results', style: { padding: 12, textAlign: 'center' } },
          React.createElement('div', { style: { color: T.textDim, fontSize: 11 } }, 'Keine Ergebnisse')
        )
      ),

      /* BREADCRUMB BAR */
      breadcrumb.length > 0 && React.createElement('div', { className: 'breadcrumb-bar', style: { top: 86 } },
        breadcrumb.map(function(bc, i) {
          var isLast = i === breadcrumb.length - 1;
          var isClickable = !isLast;
          return React.createElement(React.Fragment, { key: i },
            i > 0 && React.createElement('span', { className: 'breadcrumb-sep' }, '\u203A'),
            React.createElement('span', {
              className: 'breadcrumb-item' + (isClickable ? ' clickable' : '') + (isLast ? ' active' : ''),
              onClick: isClickable ? function() {
                if (bc.level === 'overview') {
                  navigateTo('overview');
                } else if (bc.level === 'region') {
                  navigateTo('region', { regionKey: bc.regionKey, regionLabel: bc.label });
                }
              } : undefined
            }, bc.label)
          );
        })
      ),

      /* FORMATION PATH LABEL (bottom center overlay) */
      formationLabel && React.createElement('div', { className: 'formation-path-label glass', style: { borderColor: formationColor ? ('rgba(' + parseInt(formationColor.slice(1,3),16) + ',' + parseInt(formationColor.slice(3,5),16) + ',' + parseInt(formationColor.slice(5,7),16) + ',0.3)') : 'rgba(90,110,170,0.15)', color: formationColor || T.text } },
        '\u26A1 ', formationLabel
      ),

      /* LEFT: Regionen */
      React.createElement('div', { className: pnl + ' panel-regions' },
        React.createElement('div', { className: 'panel-header' }, 'Regionen (' + sceneData.regionNodes.length + ')'),
        sceneData.regionNodes.map(function(rn) {
          return React.createElement('div', { key: rn.id, className: 'region-item', onClick: function() {
            setSel(rn.id);
            setInfo(rn);
            connectedRef.current = { nodeIds: new Set([rn.id]), threadIndices: [] };
          } },
            React.createElement('div', { className: 'region-dot', style: { background: rn.hex, boxShadow: '0 0 6px ' + rn.hex + '50' } }),
            React.createElement('div', { style: { flex: 1 } },
              React.createElement('div', { className: 'region-label', style: { color: T.text } }, rn.label),
              React.createElement('div', { className: 'region-sub' }, rn.sub)
            ),
            React.createElement('div', { className: 'region-intensity' },
              React.createElement('div', { className: 'region-intensity-fill',
                style: { width: Math.max(5, rn.intensity * 100) + '%', background: rn.hex } })
            )
          );
        })
      ),

      /* LEFT BOTTOM: Faeden-Liste */
      React.createElement('div', { className: pnl + ' panel-threads' },
        React.createElement('div', { className: 'panel-header' }, 'Faeden (' + sceneData.threads.length + ')'),
        sceneData.threads.map(function(t, i) {
          return React.createElement('div', { key: i,
            className: 'thread-item' + (selThread === i ? ' active' : ''),
            onClick: function() {
              setSelThread(selThread === i ? null : i);
              setSel(null);
              setInfo({ type: 'thread', label: t.label, hex: t.farbe, farbe: t.farbe, von: t.von, nach: t.nach, dicke: t.dicke, opacity: t.opacity, kategorie: t.kategorie, permanent: t.permanent, meta: t.meta });
              // Fire formation path for thread category
              var threadCategory = THREAD_CATEGORY_MAP[t.kategorie] || 'unknown';
              var threadFormation = FORMATION_PATHS[threadCategory] || FORMATION_PATHS.unknown;
              fireFormation(threadFormation);
            } },
            React.createElement('div', { className: 'thread-swatch', style: { background: t.farbe, color: t.farbe,
              width: Math.max(8, t.dicke * 30), height: Math.max(2, t.dicke * 5) } }),
            React.createElement('span', { className: 'thread-name', style: { fontSize: 9 } },
              t.kategorie === 'bond' && t.meta && t.meta.partner
                ? t.meta.partner + ' (' + t.meta.bond_typ + ')'
                : t.von + ' \u2192 ' + t.nach
            ),
            React.createElement('span', { className: 'thread-count', style: { fontSize: 8 } },
              (t.dicke * 100).toFixed(0) + '%'
            )
          );
        })
      ),

      /* RIGHT: DNA Drives */
      apiData && apiData.dna && React.createElement('div', { className: pnl + ' panel-dna' },
        React.createElement('div', { className: 'panel-header' }, 'DNA: ' + (apiData.dna.dna_profile || 'DEFAULT')),
        apiData.dna.dominant_drives && apiData.dna.dominant_drives.map(function(d, i) {
          return React.createElement('div', { key: i, className: 'drive-bar-container' },
            React.createElement('span', { className: 'drive-label' }, d.drive),
            React.createElement('div', { className: 'drive-bar' },
              React.createElement('div', { className: 'drive-bar-fill', style: { width: (d.value * 100) + '%',
                background: sceneData.driveNodes[i] ? sceneData.driveNodes[i].hex : '#5e7ce0' } })
            ),
            React.createElement('span', { className: 'drive-value' }, (d.value * 100).toFixed(0) + '%')
          );
        }),
        apiData.dna.beschreibung && React.createElement('div', { style: { color: T.textDim, fontSize: 8, marginTop: 6, lineHeight: 1.4 } },
          apiData.dna.beschreibung
        )
      ),

      /* HOVER */
      hov !== null && !sel && sceneData && (function() {
        var node = sceneData.allNodes.find(function(n) { return n.id === hov; });
        if (!node) return null;
        return React.createElement('div', { className: 'glass hover-tooltip' },
          React.createElement('div', { style: { display: "flex", alignItems: "center", gap: 6 } },
            React.createElement('div', { className: 'region-dot', style: { background: node.hex } }),
            React.createElement('span', { style: { color: T.text, fontSize: 11, fontWeight: 600 } }, node.label)
          ),
          React.createElement('div', { style: { color: T.textDim, fontSize: 9, marginTop: 2 } },
            node.type === 'region' && ('Aktivitaet: ' + (node.intensity * 100).toFixed(0) + '% \u00B7 Nutzung: ' + node.nutzung),
            node.type === 'bond' && ('Score: ' + node.score + ' \u00B7 Trust: ' + (node.trust * 100).toFixed(0) + '% \u00B7 ' + node.bond_typ),
            node.type === 'drive' && ('Staerke: ' + (node.value * 100).toFixed(0) + '%')
          )
        );
      })(),

      /* SELECTED INFO PANEL */
      info && React.createElement('div', { className: pnl + ' panel-info' },
        React.createElement('div', { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start" } },
          React.createElement('div', { style: { display: "flex", alignItems: "center", gap: 7 } },
            viewLevel !== 'overview' && React.createElement('button', { className: 'back-btn', onClick: function() {
              if (viewLevel === 'item') {
                navigateTo('region', { regionKey: currentRegion, regionLabel: REGIONS[currentRegion] ? REGIONS[currentRegion].label : currentRegion });
              } else {
                navigateTo('overview');
              }
            } }, '\u2190 Zurueck'),
            React.createElement('div', { className: 'region-dot',
              style: { width: 8, height: 8, background: info.hex || '#5e7ce0',
                       boxShadow: '0 0 6px ' + (info.hex || '#5e7ce0') } }),
            React.createElement('span', { style: { color: T.text, fontSize: 13, fontWeight: 600 } },
              /* Fuer Bonds: nur den Namen zeigen (ohne "(Person)"), Badge kommt separat */
              info.type === 'bond' ? (info.label || '').replace(/\s*\((?:Person|Egon|Owner|Bezugsperson)\)\s*$/, '') : info.label
            )
          ),
          React.createElement('button', { className: 'close-btn', onClick: function() {
            setSel(null); setInfo(null); setSelThread(null);
            if (viewLevel === 'item') {
              navigateTo('region', { regionKey: currentRegion, regionLabel: REGIONS[currentRegion] ? REGIONS[currentRegion].label : currentRegion });
            }
          } },
            '\u2715'
          )
        ),

        /* SUB-NODE INFO (Level 2/3) */
        info.type === 'sub_node' && renderSubNodeDetail(info, T, zoomToNode, fireFormation),

        /* REGION INFO */
        info.type === 'region' && (function() {
          var connSummary = getRegionConnectionSummary(info.region);
          return React.createElement('div', { style: { marginTop: 8 } },
            React.createElement('div', { style: { color: T.textMid, fontSize: 10 } }, info.sub),
            React.createElement('div', { style: { marginTop: 8 } },
              React.createElement('div', { style: { color: T.textDim, fontSize: 9 } }, 'Aktivitaet'),
              React.createElement('div', { className: 'info-marker-bar' },
                React.createElement('div', { className: 'info-marker-fill',
                  style: { width: Math.max(3, info.intensity * 100) + '%', background: info.hex } })
              ),
              React.createElement('div', { style: { color: T.text, fontSize: 10, marginTop: 2 } },
                (info.intensity * 100).toFixed(0) + '% \u00B7 ' + info.nutzung + ' Nutzungen'
              )
            ),
            /* Connection summary */
            React.createElement('div', { style: { marginTop: 8, padding: '6px 0', borderTop: '1px solid rgba(90,110,170,0.1)' } },
              React.createElement('div', { style: { fontSize: 9, color: T.textMid } },
                'Eingehend: ', React.createElement('b', { style: { color: T.text } }, connSummary.incoming),
                ' \u00B7 Ausgehend: ', React.createElement('b', { style: { color: T.text } }, connSummary.outgoing),
                ' \u00B7 Gesamt: ', React.createElement('b', { style: { color: T.accent } }, connSummary.incoming + connSummary.outgoing)
              ),
              connSummary.connectedRegions.length > 0 && React.createElement('div', { style: { marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 3 } },
                connSummary.connectedRegions.map(function(cr) {
                  var crDef = REGIONS[cr];
                  return React.createElement('span', { key: cr, className: 'tag-chip', style: { borderLeft: '3px solid ' + (crDef ? crDef.hex : '#5e7ce0') } },
                    crDef ? crDef.label : cr
                  );
                })
              )
            ),
            /* Verbundene Faeden */
            React.createElement('div', { style: { marginTop: 6, borderTop: '1px solid rgba(90,110,170,0.1)', paddingTop: 8 } },
              React.createElement('div', { className: 'panel-header' }, 'Verbundene Faeden'),
              sceneData.threads
                .filter(function(t) { return t.von === info.region || t.nach === info.region; })
                .map(function(t, i) {
                  return React.createElement('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', fontSize: 9, color: T.textMid } },
                    React.createElement('div', { style: { width: Math.max(6, t.dicke * 20), height: 3, borderRadius: 2, background: t.farbe } }),
                    React.createElement('span', null, t.von === info.region ? t.nach : t.von),
                    React.createElement('span', { style: { marginLeft: 'auto', color: T.textDim } }, (t.dicke * 100).toFixed(0) + '%')
                  );
                })
            ),
            /* Action buttons */
            React.createElement('div', { style: { display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' } },
              viewLevel === 'overview' && React.createElement('button', {
                className: 'deep-dive-btn',
                onClick: function() { deepDiveRegion(info.region); }
              }, 'Deep Dive \u2197'),
              React.createElement('button', {
                className: 'zoom-btn',
                onClick: function() { zoomToNode({ pos: info.pos }); }
              }, 'Hierher zoomen')
            )
          );
        })(),

        /* BOND INFO */
        info.type === 'bond' && React.createElement('div', { style: { marginTop: 8 } },
          /* Entity Badge — Mensch/EGON/Owner */
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 } },
            React.createElement('span', { style: {
              background: (info.entity_color || '#fb923c') + '22',
              border: '1px solid ' + (info.entity_color || '#fb923c') + '44',
              borderRadius: 12, padding: '2px 10px', fontSize: 10, fontWeight: 600,
              color: info.entity_color || '#fb923c',
            } }, info.entity_label || (info.bond_type === 'person' ? 'Mensch' : info.bond_type === 'owner' ? 'Bezugsperson' : 'EGON')),
            info.contact_status === 'pending' && React.createElement('span', { style: {
              background: 'rgba(251,191,36,0.15)', border: '1px solid rgba(251,191,36,0.3)',
              borderRadius: 12, padding: '2px 8px', fontSize: 9, color: '#fbbf24',
            } }, '\u23F3 Unbestaetigt'),
            React.createElement('span', { style: { color: T.textDim, fontSize: 9 } }, info.bond_typ)
          ),
          /* Stats */
          React.createElement('div', { style: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 } },
            [
              { label: 'Score', value: info.score, color: '#fb923c' },
              { label: 'Trust', value: (info.trust * 100).toFixed(0) + '%', color: '#4ade80' },
              { label: 'Familiarity', value: (info.familiarity * 100).toFixed(0) + '%', color: '#60a5fa' },
            ].map(function(s, i) {
              return React.createElement('div', { key: i, style: { textAlign: 'center' } },
                React.createElement('div', { style: { color: s.color, fontSize: 16, fontWeight: 700 } }, s.value),
                React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, s.label)
              );
            })
          ),
          /* Score bar */
          React.createElement('div', { className: 'info-marker-bar', style: { marginBottom: 4 } },
            React.createElement('div', { className: 'info-marker-fill',
              style: { width: (info.staerke * 100) + '%', background: info.hex } })
          ),
          /* Resonanz bar (if pairing) */
          info.resonanz != null && React.createElement('div', { style: { marginTop: 4 } },
            React.createElement('div', { style: { color: T.textDim, fontSize: 9 } }, 'Resonanz'),
            React.createElement('div', { className: 'gauge-bar' },
              React.createElement('div', { className: 'gauge-fill', style: { width: (info.resonanz * 100) + '%', background: '#e91e63' } })
            )
          ),
          React.createElement('div', { style: { fontSize: 9, color: T.textDim } },
            info.hat_narbe && React.createElement('span', { style: { color: '#ef4444', marginRight: 8 } }, '\u26A0 Hat Narbe'),
            info.emotional_debt > 0 && React.createElement('span', { style: { color: '#fbbf24', marginRight: 8 } }, 'Schuld: ' + info.emotional_debt)
          ),
          React.createElement('div', { style: { fontSize: 9, color: T.textDim, marginTop: 2 } },
            'Attachment: ' + info.attachment + ' \u00B7 Letzte Interaktion: ' + (info.last_interaction || 'nie')
          ),
          /* Chat count + first interaction */
          (info.chat_count || info.first_interaction) && React.createElement('div', { style: { fontSize: 9, color: T.textDim, marginTop: 2 } },
            info.chat_count ? ('Chats: ' + info.chat_count) : '',
            info.first_interaction ? (' \u00B7 Erstes Treffen: ' + info.first_interaction) : ''
          ),
          /* Social map */
          info.social_map && React.createElement('div', { className: 'social-card', style: { marginTop: 6 } },
            React.createElement('div', { className: 'panel-header' }, 'Social Map'),
            info.social_map.erster_eindruck && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } },
              'Erster Eindruck: ', info.social_map.erster_eindruck),
            info.social_map.aktueller_eindruck && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 2 } },
              'Aktueller Eindruck: ', info.social_map.aktueller_eindruck)
          ),
          /* Observations (scrollable, ALL of them) */
          info.observations && info.observations.length > 0 && React.createElement('div', { style: { marginTop: 8, borderTop: '1px solid rgba(90,110,170,0.1)', paddingTop: 6 } },
            React.createElement('div', { className: 'panel-header' }, 'Was ich weiss (' + info.observations.length + ')'),
            React.createElement('div', { className: 'obs-scroll' },
              info.observations.map(function(obs, i) {
                return React.createElement('div', { key: i, style: { fontSize: 9, color: T.textMid, marginBottom: 3, lineHeight: 1.3,
                                          paddingLeft: 8, borderLeft: '2px solid ' + (info.hex || '#fb923c') + '33' } },
                  obs
                );
              })
            )
          ),
          /* Bond History */
          info.history && info.history.length > 0 && React.createElement('div', { style: { marginTop: 8, borderTop: '1px solid rgba(90,110,170,0.1)', paddingTop: 6 } },
            React.createElement('div', { className: 'panel-header' }, 'Geschichte (' + info.history.length + ')'),
            info.history.slice(-8).map(function(h, i) {
              return React.createElement('div', { key: i, style: { fontSize: 8, color: T.textMid, marginBottom: 4, lineHeight: 1.3 } },
                React.createElement('span', { style: { color: T.textDim } }, h.date), ' ',
                (h.event || '').slice(0, 80),
                h.trust_before !== h.trust_after && React.createElement('span', { style: { color: h.trust_after > h.trust_before ? '#4ade80' : '#ef4444' } },
                  ' Trust: ' + h.trust_before + ' \u2192 ' + h.trust_after
                )
              );
            })
          ),
          /* Action buttons */
          React.createElement('div', { style: { display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' } },
            React.createElement('button', {
              className: 'zoom-btn',
              onClick: function() { zoomToNode({ pos: info.pos }); }
            }, 'Hierher zoomen'),
            React.createElement('button', {
              className: 'formation-btn',
              onClick: function() { fireFormation(FORMATION_PATHS.bond); }
            }, '\u26A1 Entstehungspfad zeigen')
          )
        ),

        /* DRIVE INFO */
        info.type === 'drive' && React.createElement('div', { style: { marginTop: 8 } },
          React.createElement('div', { style: { color: info.hex, fontSize: 24, fontWeight: 700 } },
            (info.value * 100).toFixed(0) + '%'
          ),
          React.createElement('div', { className: 'info-marker-bar' },
            React.createElement('div', { className: 'info-marker-fill',
              style: { width: (info.value * 100) + '%', background: info.hex } })
          ),
          React.createElement('div', { style: { color: T.textDim, fontSize: 9, marginTop: 4 } },
            'Panksepp Drive \u00B7 Beeinflusst DNA-Morphologie'
          ),
          /* Action buttons */
          React.createElement('div', { style: { display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' } },
            React.createElement('button', {
              className: 'zoom-btn',
              onClick: function() { zoomToNode({ pos: info.pos }); }
            }, 'Hierher zoomen'),
            React.createElement('button', {
              className: 'formation-btn',
              onClick: function() { fireFormation(FORMATION_PATHS.drive); }
            }, '\u26A1 Entstehungspfad zeigen')
          )
        ),

        /* THREAD INFO */
        info.type === 'thread' && React.createElement('div', { style: { marginTop: 8 } },
          React.createElement('div', { style: { color: T.textMid, fontSize: 10 } },
            info.von + ' \u2192 ' + info.nach
          ),
          React.createElement('div', { style: { display: 'flex', gap: 12, marginTop: 8 } },
            React.createElement('div', { style: { textAlign: 'center' } },
              React.createElement('div', { style: { color: info.farbe, fontSize: 18, fontWeight: 700 } }, (info.dicke * 100).toFixed(0) + '%'),
              React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, 'Dicke')
            ),
            React.createElement('div', { style: { textAlign: 'center' } },
              React.createElement('div', { style: { color: T.text, fontSize: 18, fontWeight: 700 } }, (info.opacity * 100).toFixed(0) + '%'),
              React.createElement('div', { style: { color: T.textDim, fontSize: 8 } }, 'Opacity')
            )
          ),
          React.createElement('div', { style: { fontSize: 9, color: T.textDim, marginTop: 6 } },
            'Kategorie: ' + info.kategorie + ' \u00B7 ' + (info.permanent ? 'Permanent' : 'Temporaer')
          ),
          info.meta && info.meta.partner && React.createElement('div', { style: { fontSize: 9, color: T.textMid, marginTop: 4 } },
            'Partner: ' + info.meta.partner + ' \u00B7 Typ: ' + info.meta.bond_typ + ' \u00B7 Staerke: ' + (info.meta.bond_staerke * 100).toFixed(0) + '%',
            info.meta.hat_narbe && React.createElement('span', { style: { color: '#ef4444' } }, ' \u26A0 Narbe')
          ),
          /* Action buttons */
          React.createElement('div', { style: { display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' } },
            React.createElement('button', {
              className: 'formation-btn',
              onClick: function() {
                var threadCategory = THREAD_CATEGORY_MAP[info.kategorie] || 'unknown';
                var threadFormation = FORMATION_PATHS[threadCategory] || FORMATION_PATHS.unknown;
                fireFormation(threadFormation);
              }
            }, '\u26A1 Entstehungspfad zeigen')
          )
        )
      ),

      /* HINT */
      !sel && !info && viewLevel === 'overview' && React.createElement('div', { className: 'hint' },
        'Ziehen = Drehen \u00B7 Hover = Info \u00B7 Klick = Details \u00B7 Doppelklick = Deep Dive',
        React.createElement('br'),
        'Mausrad = Zoom \u00B7 Escape = Zurueck \u00B7 Suche = oben Mitte',
        React.createElement('br'),
        React.createElement('span', { style: { color: T.accent } }, 'Jeder Punkt = echte Daten')
      ),

      /* CANVAS */
      React.createElement('div', { ref: mountRef, id: 'three-canvas',
        className: hov !== null ? 'hovering' : '',
        style: { width: "100%", height: "100%" },
        onMouseDown: onDown, onMouseMove: onMove, onClick: onClick, onDoubleClick: onDblClick })
    )
  );
}

window.EgonNeuroMap = EgonNeuroMap;
