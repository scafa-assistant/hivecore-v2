# EGON Projekt — Konventionen

> **Verwandte Dateien:** [INDEX.md](INDEX.md), [GLOSSAR.md](GLOSSAR.md)
> **Zuletzt aktualisiert:** 2026-02-26

---

## Code-Sprache

| Bereich | Sprache |
|---------|---------|
| Code (Variablen, Funktionen) | Englisch |
| Code-Kommentare | Deutsch oder Englisch |
| Motor-Wörter | **Deutsch** (z.B. "nicken", "winken") |
| Commit-Messages | Englisch |
| Dokumentation | Deutsch |
| EGON-Organe (dna.md etc.) | Deutsch |

## Datei-Benennung

| Typ | Konvention | Beispiel |
|-----|-----------|---------|
| GLB-Clips | snake_case | `waving_right.glb` |
| Motor-Wörter | snake_case deutsch | `"kopf_schuetteln"` |
| TypeScript | camelCase | `skeletalRenderer.ts` |
| Python | snake_case | `prompt_builder_v2.py` |
| EGON-Organe | snake_case | `inner_voice.md` |
| Docs | SCREAMING_CASE | `ACHSEN.md` |

## Motor-Vocabulary Einträge

Jedes Motor-Wort folgt dieser Struktur:
```json
{
  "wort_name": {
    "id": "MOT_UNIQUE_ID",
    "category": "posture | gesture | expression | locomotion",
    "type": "static | sequence",
    "duration_ms": 500-1400,
    "bones": { ... },
    "easing": "ease_in_out",
    "loopable": false,
    "blendable": true,
    "glb_fallback": "clip_name | null"
  }
}
```

## Commit-Messages

Format: `Bereich: Kurzbeschreibung`

Beispiele:
- `Motor: Fix arm axis ry instead of rx`
- `App: Add waving_right GLB clip`
- `Server: Deploy motor_vocabulary v1.3`
- `Docs: Update ACHSEN.md with head values`

## Docs-Aktualisierung

Jede Datei hat:
- **Oben:** Verwandte Dateien, Zuletzt aktualisiert
- **Unten:** Siehe auch, Zurück-Link
- Datum-Format: `YYYY-MM-DD`
- Neue Einträge in Logs: **OBEN** (neueste zuerst)

---

*Zurück zu: [INDEX.md](INDEX.md)*
