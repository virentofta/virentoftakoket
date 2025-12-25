from __future__ import annotations

import uuid
from pathlib import Path

from datetime import date, timedelta

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.config import settings
from models.recipe import Ingredient
from services.menu_service import menu_service
from services.profile_service import profile_service
from services.recipe_service import recipe_service
from services.shopping_service import shopping_service

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.template_dir))


def _resolve_profile(profile_id: int | None) -> int:
    if profile_id is None:
        return 1
    return profile_id if profile_service.get_profile(profile_id) else 1


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, profile_id: int | None = None):
    """Startsida med enkla exempelvärden."""
    active_profile_id = _resolve_profile(profile_id)
    context = {
        "request": request,
        "title": "Virentoftakoket",
        "subtitle": "Snart färdig!",
        "items": ["Recept", "Veckomeny", "Inköpslista"],
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("index.html", context)


@router.get("/recipes", response_class=HTMLResponse)
async def recipes_page(request: Request, profile_id: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    recipes = recipe_service.list_recipes(profile_id=active_profile_id)
    current_week = date.today().isocalendar().week
    next_week = current_week + 1 if current_week < 52 else 1
    current_year = date.today().isocalendar().year
    next_year = current_year + 1 if next_week == 1 and current_week == 52 else current_year
    context = {
        "request": request,
        "title": "Recept",
        "recipes": recipes,
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
        "current_week": current_week,
        "next_week": next_week,
        "current_year": current_year,
        "next_year": next_year,
    }
    return templates.TemplateResponse("recipes/list.html", context)


@router.post("/recipes/menu")
async def create_weekly_menu(
    profile_id: int | None = Form(None),
    recipe_ids: str = Form(""),
    week_number: int | None = Form(None),
    year: int | None = Form(None),
):
    """Skapa veckomeny från valda recept-ID:n (ordning: Mån-Sön)."""
    active_profile_id = _resolve_profile(profile_id)
    ids = [int(x) for x in recipe_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Inga recept valda")
    resolved_week = week_number or date.today().isocalendar().week
    resolved_year = year or date.today().isocalendar().year
    menu_service.replace_menu(ids, profile_id=active_profile_id, week_number=resolved_week, year=resolved_year)
    return RedirectResponse(
        url=f"/menu?profile_id={active_profile_id}&week_number={resolved_week}&year={resolved_year}",
        status_code=303,
    )


@router.post("/menu/shopping")
async def create_shopping_list(profile_id: int | None = Form(None), week_number: int | None = Form(None), year: int | None = Form(None)):
    """Generera inköpslista utifrån aktuell veckomeny."""
    active_profile_id = _resolve_profile(profile_id)
    menu = menu_service.get_menu(profile_id=active_profile_id, week_number=week_number, year=year)
    recipe_ids = [entry.recipe_id for entry in menu.entries if entry.recipe_id]
    recipes = [recipe_service.get_recipe(rid) for rid in recipe_ids]
    recipes = [r for r in recipes if r]
    if not recipes:
        raise HTTPException(status_code=400, detail="Ingen veckomeny att skapa lista från")
    shopping_service.set_from_recipes(recipes, profile_id=active_profile_id)
    resolved_week = week_number or menu.week_number or date.today().isocalendar().week
    resolved_year = year or getattr(menu, "year", None) or date.today().isocalendar().year
    return RedirectResponse(
        url=f"/menu?profile_id={active_profile_id}&week_number={resolved_week}&year={resolved_year}", status_code=303
    )


@router.post("/menu/remove")
async def remove_menu_entry(
    profile_id: int | None = Form(None),
    day: str = Form(...),
    week_number: int | None = Form(None),
    year: int | None = Form(None),
):
    active_profile_id = _resolve_profile(profile_id)
    menu_service.remove_entry(day, profile_id=active_profile_id, week_number=week_number, year=year)
    # Bygg om inköpslistan från återstående recept i menyn
    menu = menu_service.get_menu(profile_id=active_profile_id, week_number=week_number, year=year)
    recipe_ids = [entry.recipe_id for entry in menu.entries if entry.recipe_id]
    recipes = [recipe_service.get_recipe(rid) for rid in recipe_ids]
    recipes = [r for r in recipes if r]
    shopping_service.set_from_recipes(recipes, profile_id=active_profile_id)
    resolved_week = week_number or menu.week_number or date.today().isocalendar().week
    resolved_year = year or getattr(menu, "year", None) or date.today().isocalendar().year
    return RedirectResponse(
        url=f"/menu?profile_id={active_profile_id}&week_number={resolved_week}&year={resolved_year}",
        status_code=303,
    )


@router.post("/menu/responsible")
async def set_responsible(profile_id: int | None = Form(None), responsible_profile_id: int | None = Form(None), week_number: int | None = Form(None), year: int | None = Form(None)):
    active_profile_id = _resolve_profile(profile_id)
    menu_service.set_responsible(
        profile_id=active_profile_id,
        responsible_profile_id=responsible_profile_id,
        week_number=week_number,
        year=year,
    )
    resolved_week = week_number or date.today().isocalendar().week
    resolved_year = year or date.today().isocalendar().year
    return RedirectResponse(
        url=f"/menu?profile_id={active_profile_id}&week_number={resolved_week}&year={resolved_year}", status_code=303
    )


@router.post("/menu/reorder")
async def reorder_menu(profile_id: int | None = Form(None), recipe_ids: str = Form(""), week_number: int | None = Form(None), year: int | None = Form(None)):
    """Uppdatera veckomenyn med ny ordning (mappar till Mån–Sön)."""
    active_profile_id = _resolve_profile(profile_id)
    ids = [int(x) for x in recipe_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Inga recept att ordna")
    resolved_week = week_number or date.today().isocalendar().week
    resolved_year = year or date.today().isocalendar().year
    menu_service.replace_menu(ids, profile_id=active_profile_id, week_number=resolved_week, year=resolved_year)
    return RedirectResponse(url=f"/menu?profile_id={active_profile_id}&week_number={resolved_week}&year={resolved_year}", status_code=303)


@router.post("/menu/add")
async def add_menu_recipes(
    profile_id: int | None = Form(None),
    recipe_ids: list[int] = Form([]),
    week_number: int | None = Form(None),
    year: int | None = Form(None),
):
    """Fyll på tomma dagar i en befintlig veckomeny."""
    active_profile_id = _resolve_profile(profile_id)
    cleaned_ids = [rid for rid in recipe_ids if rid]
    resolved_week = week_number or date.today().isocalendar().week
    resolved_year = year or date.today().isocalendar().year
    menu_service.append_recipes(cleaned_ids, profile_id=active_profile_id, week_number=resolved_week, year=resolved_year)
    return RedirectResponse(
        url=f"/menu?profile_id={active_profile_id}&week_number={resolved_week}&year={resolved_year}", status_code=303
    )


@router.get("/recipes/new", response_class=HTMLResponse)
async def new_recipe_form(request: Request, profile_id: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    context = {
        "request": request,
        "title": "Nytt recept",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("recipes/new.html", context)


@router.post("/recipes/new")
async def create_recipe(
    request: Request,
    title: str = Form(...),
    description: str | None = Form(None),
    servings: str | None = Form(None),
    image_url: str | None = Form(None),
    image_file: UploadFile | None = File(None),
    ingredients_text: str = Form(""),
    steps_text: str = Form(""),
    tags_text: str = Form(""),
    profile_id: int | None = Form(None),
):
    active_profile_id = _resolve_profile(profile_id)
    servings_value: int | None = None
    if servings:
        try:
            servings_value = int(servings)
        except ValueError:
            servings_value = None

    ingredients = []
    for line in ingredients_text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        parts = clean.split(" ", 1)
        amount = parts[0] if len(parts) > 1 else None
        name = parts[1] if len(parts) > 1 else parts[0]
        ingredients.append({"name": name, "amount": amount})

    steps = [s.strip() for s in steps_text.splitlines() if s.strip()]
    tags = [t.strip() for t in tags_text.split(",") if t.strip()]

    # Spara uppladdad bild om den finns
    uploaded_url: str | None = None
    if image_file and image_file.filename:
        images_dir = settings.data_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(image_file.filename).suffix
        filename = f"{uuid.uuid4().hex}{suffix}"
        target_path = images_dir / filename
        with target_path.open("wb") as f:
            f.write(await image_file.read())
        uploaded_url = f"/uploads/{filename}"

    recipe = recipe_service.add_recipe(
        title=title,
        description=description,
        ingredients=[Ingredient(**ing) for ing in ingredients],
        steps=steps,
        tags=tags,
        created_by=active_profile_id,
        servings=servings_value,
        image_url=uploaded_url or image_url or None,
    )

    redirect_url = f"/recipes/{recipe.id}?profile_id={active_profile_id}"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
async def recipe_detail(request: Request, recipe_id: int, profile_id: int | None = None):
    recipe = recipe_service.get_recipe(recipe_id, include_archived=False)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    active_profile_id = _resolve_profile(profile_id)
    context = {
        "request": request,
        "title": recipe.title,
        "recipe": recipe,
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("recipes/detail.html", context)


@router.get("/menu", response_class=HTMLResponse)
async def weekly_menu(request: Request, profile_id: int | None = None, week_number: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    today = date.today()
    base_week = week_number or today.isocalendar().week
    base_year = request.query_params.get("year")
    base_year = int(base_year) if base_year and base_year.isdigit() else today.isocalendar().year
    try:
        base_date = date.fromisocalendar(base_year, base_week, 1)
    except ValueError:
        base_date = today
        base_week = today.isocalendar().week
        base_year = today.isocalendar().year

    prev_date = base_date - timedelta(days=7)
    next_date = base_date + timedelta(days=7)

    menu = menu_service.get_menu(profile_id=active_profile_id, week_number=base_week, year=base_year)
    recipes = recipe_service.list_recipes(profile_id=active_profile_id)
    recipe_lookup = {r.id: r.title for r in recipes}
    recipes_by_id = {r.id: r for r in recipes}
    shopping_list = shopping_service.get_list(profile_id=active_profile_id)
    responsible = (
        profile_service.get_profile(menu.responsible_profile_id) if getattr(menu, "responsible_profile_id", None) else None
    )
    context = {
        "request": request,
        "title": "Veckomeny",
        "menu": menu,
        "recipe_lookup": recipe_lookup,
        "recipes_by_id": recipes_by_id,
        "recipes": recipes,
        "shopping_list": shopping_list,
        "current_week": base_week,
        "current_year": base_year,
        "prev_week": prev_date.isocalendar().week,
        "prev_year": prev_date.isocalendar().year,
        "next_week": next_date.isocalendar().week,
        "next_year": next_date.isocalendar().year,
        "profiles": profile_service.list_profiles(),
        "responsible": responsible,
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("menu/week.html", context)
