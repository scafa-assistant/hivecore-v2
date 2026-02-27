# EGON Projekt — Aktueller Status

> **Zweck:** Snapshot des Projektstands. Wird nach JEDER Session aktualisiert.
> Claude Code: Lies diese Datei VOR jeder Aufgabe — sie sagt dir wo wir stehen.
> **Zuletzt aktualisiert:** 2026-02-27

---

## Systemzustand

| Komponente | Status | Details |
|-----------|--------|---------|
| Server (HiveCore v2) | ✅ Läuft | 159.69.157.42, systemd aktiv |
| Adam #001 | ✅ Aktiv | body.md + dna.md deployed, Motor funktioniert |
| Eva #002 | ⏳ Ausstehend | Motor-Fixes noch nicht übertragen |
| App (EgonsDash) | ✅ Läuft | APK: v2.3.8-LAYER3 (262 MB) |
| Motor-System | ✅ Funktioniert | v1.9, 38 Wörter, Layer-System aktiv, 3 GLB-Fallbacks, Hips-Translation |
| Moonshot Hit-Rate | ✅ ~100% | Few-Shot Primer in chat.py (bei leerer History) |

---

## Was funktioniert

- Adam steht entspannt (idle_natural.glb), kein T-Pose Flash
- Winken rechts + links (echte GLB-Clips via glb_fallback)
- Kopfschütteln (echte GLB-Animation head_shake.glb)
- Nicken, Kopf neigen, Kopf drehen links/rechts (Motor-Keyframes)
- hand_heben, beide_haende_heben (Achsen korrigiert v1.4)
- "verwirrt" Animation (confused.glb mit Hips-Translation, 20 Bones, v1.9)
- Kein Drift-Bug mehr (Snapshot-basierte Offsets)
- Layer-System: Mixer IMMER aktiv + Motor additiv
- Async Post-Processing: Response kommt sofort nach bone_update (-15 bis -60s)
- Heuristische Tier-Erkennung statt LLM-Call (-300ms)
- Dokumentationssystem (.claude/) ist aufgesetzt

## Was kaputt / ungetestet ist

- Eva #002 — hat noch keinen der Motor-Fixes
- `kopf_drehen_links` / `kopf_drehen_rechts` — Achsen ungetestet auf Gerät

## Aktive Baustellen

1. **Eva übertragen** — Gleiche Motor-Fixes wie Adam
2. **Weitere GLB-Fallbacks** — nicken, zeigen etc. evaluieren
3. **Vokabular erweitern** — Richtung ~60 Wörter

---

## Nächste Schritte (Priorität)

| # | Aufgabe | Bereich | Aufwand |
|---|---------|---------|---------|
| 1 | Eva Motor-System deployen | Server/App | Mittel |
| 2 | Kopf-Gesten auf Gerät testen | App/Motor | Klein |
| 3 | Vokabular erweitern (~60 Wörter) | Motor | Groß |
| 4 | Phase 3: Motor-Skill Learning | Motor/Server | Groß |

---

## Letzte Änderungen

### 2026-02-27 — Performance-Fix: Async Post-Processing + Heuristic Tier
- **Fix 1:** Post-Processing (Thalamus, Emotion, Bonds, Episodes, Memory etc.) laeuft jetzt async im Background via `asyncio.create_task()`. HTTP-Response wird SOFORT nach bone_update zurueckgegeben. Einsparung: -15 bis -60 Sekunden pro Chat.
- **Fix 2:** `decide_tier()` nutzt Keyword-Heuristik statt Moonshot LLM-Call. Einsparung: -300ms pro Chat.
- Inner Voice bewusst BEIBEHALTEN (gibt Adam Seele, 800ms marginal).
- Motor Vocabulary v1.9: "verwirrt" mit Hips-Translation (tx/tz) fuer natuerliches Hueftschwingen.

### 2026-02-26 — Motor v1.4 + GLB-Fallbacks + Docs-Upgrade
- hand_heben/beide_haende_heben: rz-Bug gefixt (Arm ging nach hinten statt hoch)
- kopf_schuetteln: GLB-Fallback head_shake.glb eingebunden
- kopf_drehen_links/rechts: Neue Motor-Wörter hinzugefügt
- Motor Vocabulary v1.3 → v1.4 (38 Wörter)
- APK: LAYER3 (262 MB, +head_shake.glb)
- Memory-System: MEMORY.md → Memory Bank (5 Topic-Files)
- CLAUDE.md: Self-Update Protocol erweitert, veraltete Infos korrigiert

### 2026-02-26 — Motor-System Debug & Layer-System
- Drift-Bug gefixt (Snapshot-basierte Offsets statt +=)
- T-Pose Flash gefixt (Layer-System: Mixer läuft immer)
- Achsen-Map komplett korrigiert via GLB-Extraktion
- 12 nicht-benutzte GLBs gelöscht (730→245 MB APK)
- motor_vocabulary.json v1.2→v1.3
- Komplettes Dokumentationssystem (.claude/) erstellt
- body.md + dna.md auf Produktionsserver deployed

---

## Deployment-Stand

| Datei | Lokal | Server | Sync? |
|-------|-------|--------|-------|
| motor_vocabulary.json | v1.9 | v1.9 | ✅ |
| body.md (Adam) | aktuell | aktuell | ✅ |
| dna.md (Adam) | aktuell | aktuell | ✅ |
| ego.md (Adam) | aktuell | aktuell | ✅ |
| body.md (Eva) | aktuell | VERALTET | ❌ |
| APK | v2.3.8-LAYER3 | — | N/A |

---

*Verwandte Dateien: [INDEX.md](INDEX.md) · [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md)*
*Aktualisiert von: Performance-Fix Session 2026-02-27*
