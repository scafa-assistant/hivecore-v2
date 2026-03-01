/**
 * EGON NeuroMap — API Client
 *
 * Alle 7 Brain-Endpoints + Profile + EGON-Liste.
 * BASE wird dynamisch bestimmt: same-origin wenn served vom HiveCore,
 * oder explizit gesetzt fuer lokale Entwicklung.
 */

const BASE = (() => {
  // Wenn von HiveCore served: same-origin nutzen
  if (window.location.port === '8001' || window.location.pathname.startsWith('/neuromap')) {
    return window.location.origin + '/api/egon';
  }
  // Lokale Entwicklung: direkt zum Server
  return 'http://159.69.157.42:8001/api/egon';
})();

const API_ROOT = BASE.replace('/api/egon', '/api');

// ================================================================
// Hilfsfunktionen
// ================================================================

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn(`[NeuroMap API] ${url} failed:`, err.message);
    return null;
  }
}

// ================================================================
// EGON-Liste (fuer Selector)
// ================================================================

async function fetchEgonList() {
  const data = await fetchJSON(API_ROOT.replace('/api', '/'));
  if (!data || !data.egons) return [];
  return data.egons; // ['abel_006', 'ada_005', 'adam_001', ...]
}

// ================================================================
// 1. Brain Snapshot — Kompletter Faden-Zustand
// ================================================================

async function fetchSnapshot(egonId) {
  return await fetchJSON(`${BASE}/${egonId}/brain/snapshot`);
}

// ================================================================
// 2. Brain Events — Live-Updates (Polling)
// ================================================================

async function fetchEvents(egonId, since = 0, clear = false) {
  const params = new URLSearchParams();
  if (since > 0) params.set('since', since);
  if (clear) params.set('clear', 'true');
  const qs = params.toString();
  return await fetchJSON(`${BASE}/${egonId}/brain/events${qs ? '?' + qs : ''}`);
}

// ================================================================
// 3. Bonds — Alle Beziehungen
// ================================================================

async function fetchBonds(egonId) {
  return await fetchJSON(`${BASE}/${egonId}/brain/bonds`);
}

// ================================================================
// 4. Interactions — Chat-Histories + Bond-Daten
// ================================================================

async function fetchInteractions(egonId) {
  return await fetchJSON(`${BASE}/${egonId}/brain/interactions`);
}

// ================================================================
// 5. Regions — Aktivitaets-Heatmap
// ================================================================

async function fetchRegions(egonId) {
  return await fetchJSON(`${BASE}/${egonId}/brain/regions`);
}

// ================================================================
// 6. DNA — Morphologie + Drives
// ================================================================

async function fetchDNA(egonId) {
  return await fetchJSON(`${BASE}/${egonId}/brain/dna`);
}

// ================================================================
// 7. Decisions — Kalibrierungs-Log (Patch 17)
// ================================================================

async function fetchDecisions(egonId, since = 0) {
  const qs = since > 0 ? `?since=${since}` : '';
  return await fetchJSON(`${BASE}/${egonId}/brain/decisions${qs}`);
}

// ================================================================
// Profile — Name, Avatar, Version
// ================================================================

async function fetchProfile(egonId) {
  return await fetchJSON(`${API_ROOT}/egon/${egonId}/profile`);
}

// ================================================================
// Kompletter Brain-Load (alle Daten auf einmal)
// ================================================================

async function loadFullBrain(egonId) {
  const [snapshot, bonds, regions, dna, decisions, profile] = await Promise.all([
    fetchSnapshot(egonId),
    fetchBonds(egonId),
    fetchRegions(egonId),
    fetchDNA(egonId),
    fetchDecisions(egonId),
    fetchProfile(egonId),
  ]);

  return {
    snapshot,   // faeden[], statistik
    bonds,      // bonds[] mit faden-rendering-daten
    regions,    // regionen[] mit intensitaet
    dna,        // dominant_drives, morphologie_modifikatoren
    decisions,  // kalibrierungs-log
    profile,    // name, version, etc.
    egonId,
    loadedAt: Date.now(),
  };
}

// ================================================================
// 8. Region Detail — Deep-Dive in einzelne Hirnregion
// ================================================================

async function fetchRegionDetail(egonId, regionName) {
  return await fetchJSON(`${BASE}/${egonId}/brain/region/${regionName}`);
}

// ================================================================
// 9. Diary — Owner + Self Diary
// ================================================================

async function fetchDiary(egonId, limit = 10) {
  return await fetchJSON(`${BASE}/${egonId}/brain/diary?limit=${limit}`);
}

// ================================================================
// 10. Brain Search — Volltextsuche ueber alle Organe
// ================================================================

async function searchBrain(egonId, query) {
  if (!query || query.trim().length === 0) return null;
  return await fetchJSON(`${BASE}/${egonId}/brain/search?q=${encodeURIComponent(query.trim())}`);
}

// Export fuer globalen Zugriff (kein module system, CDN-basiert)
window.NeuroMapAPI = {
  fetchEgonList,
  fetchSnapshot,
  fetchEvents,
  fetchBonds,
  fetchInteractions,
  fetchRegions,
  fetchDNA,
  fetchDecisions,
  fetchProfile,
  fetchRegionDetail,
  fetchDiary,
  searchBrain,
  loadFullBrain,
  BASE,
};
