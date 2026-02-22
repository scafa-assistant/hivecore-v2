"""Skills-Endpoint — Suchen, Installieren und Auflisten von Skills.

Nutzt die bestehende Pipeline aus engine/skill_installer.py:
  search_skills()  — Sucht auf skills.sh (synchron, wird in Thread gewrapped)
  install_skill()  — 7-Phasen Pipeline mit Security-Scan (async)

Endpoints:
  POST /api/skills/search   — Skills suchen
  POST /api/skills/install  — Skill installieren (mit Scan!)
  GET  /api/skills/list     — Installierte Skills auflisten
"""

import asyncio
from pathlib import Path
from typing import Optional, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from config import EGON_DATA_DIR
from engine.skill_installer import search_skills, install_skill
from engine.organ_reader import read_yaml_organ

router = APIRouter()


# ================================================================
# Request / Response Models
# ================================================================

class SkillSearchRequest(BaseModel):
    query: str


class SkillSearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    total: int


class SkillInstallRequest(BaseModel):
    egon_id: str = 'adam_001'
    skill_url: str  # z.B. 'vercel/react-best-practices'


class SkillInstallResponse(BaseModel):
    status: str  # installed | blocked | pending_approval | error
    skill: Optional[str] = None
    reason: Optional[str] = None
    scan_result: Optional[str] = None
    temp_path: Optional[str] = None  # Bei pending_approval


class SkillListResponse(BaseModel):
    egon_id: str
    skills: list[dict[str, Any]]
    count: int


# ================================================================
# Endpoints
# ================================================================

@router.post('/skills/search', response_model=SkillSearchResponse)
async def skills_search(req: SkillSearchRequest):
    """Sucht Skills auf skills.sh.

    search_skills() ist synchron (npx CLI Call) — wird in Thread gewrapped.
    """
    results = await asyncio.to_thread(search_skills, req.query)
    return SkillSearchResponse(
        query=req.query,
        results=results,
        total=len(results),
    )


@router.post('/skills/install', response_model=SkillInstallResponse)
async def skills_install(req: SkillInstallRequest):
    """Installiert einen Skill von skills.sh — MIT Sicherheits-Scan.

    Pipeline: Download → Scan → Entscheidung → Install → Register → InnerVoice
    """
    result = await install_skill(req.egon_id, req.skill_url)
    return SkillInstallResponse(
        status=result.get('status', 'error'),
        skill=result.get('skill'),
        reason=result.get('reason'),
        scan_result=result.get('scan_result'),
        temp_path=result.get('temp_path'),
    )


@router.get('/skills/list', response_model=SkillListResponse)
async def skills_list(egon_id: str = Query(default='adam_001')):
    """Listet installierte Skills fuer einen EGON auf.

    Liest skills.yaml aus capabilities/.
    """
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    skills = []

    if skills_data and isinstance(skills_data, dict):
        skills = skills_data.get('skills', [])
        if not isinstance(skills, list):
            skills = []

    return SkillListResponse(
        egon_id=egon_id,
        skills=skills,
        count=len(skills),
    )
