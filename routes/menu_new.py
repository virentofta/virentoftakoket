from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.config import settings
from services.menu_service import menu_service
from services.profile_service import profile_service
from services.recipe_service import recipe_service

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.template_dir))


def _resolve_profile(profile_id: int | None) -> int:
    if profile_id is None:
        return 1
    return profile_id if profile_service.get_profile(profile_id) else 1


@router.get("/menu/new", response_class=HTMLResponse)
async def new_menu(
    request: Request,
    profile_id: int | None = None,
    week_number: int | None = None,
    year: int | None = None,
    responsible_profile_id: int | None = None,
    q: str | None = None,
):
    active_profile_id = _resolve_profile(profile_id)
    current = date.today()
    selected_week = week_number or current.isocalendar().week
    selected_year = year or current.isocalendar().year

    recipes = recipe_service.search_recipes(q, profile_id=active_profile_id) if q else recipe_service.list_recipes(profile_id=active_profile_id)
    responsible = profile_service.get_profile(responsible_profile_id) if responsible_profile_id else None

    context = {
        "request": request,
        "title": "Skapa veckomeny",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
        "current_week": selected_week,
        "current_year": selected_year,
        "responsible": responsible,
        "recipes": recipes,
        "search_query": q or "",
    }
    return templates.TemplateResponse("menu/new.html", context)


@router.post("/menu/create")
async def create_menu(
    profile_id: int | None = Form(None),
    week_number: int = Form(...),
    year: int = Form(...),
    responsible_profile_id: int | None = Form(None),
    recipe_ids: str = Form(""),
):
    active_profile_id = _resolve_profile(profile_id)
    ids = [int(x) for x in recipe_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Inga recept valda")
    menu_service.replace_menu(ids, profile_id=active_profile_id, week_number=week_number, year=year)
    if responsible_profile_id:
        menu_service.set_responsible(
            profile_id=active_profile_id,
            responsible_profile_id=responsible_profile_id,
            week_number=week_number,
            year=year,
        )
    return RedirectResponse(
        url=f"/menu?profile_id={active_profile_id}&week_number={week_number}&year={year}",
        status_code=303,
    )
