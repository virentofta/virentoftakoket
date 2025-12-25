from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import datetime
import zipfile

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from core.config import settings
from models.recipe import Ingredient
from models.units import UnitCategory, get_all_units
from services.profile_service import profile_service
from services.recipe_service import recipe_service
from core.database import connection_scope

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.template_dir))


def _resolve_profile(profile_id: int | None) -> int:
    if profile_id is None:
        return 1
    return profile_id if profile_service.get_profile(profile_id) else 1


def _serialize_recipe(recipe):
    return {
        "id": recipe.id,
        "title": recipe.title,
        "description": recipe.description or "",
        "servings": recipe.servings,
        "created_by": recipe.created_by,
    }


@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request, profile_id: int | None = None):
    """Adminöversikt med genvägar."""
    active_profile_id = _resolve_profile(profile_id)
    context = {
        "request": request,
        "title": "Admin",
        "subtitle": "Hantera recept och profiler",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("admin/import.html", context)


@router.get("/recipes", response_class=HTMLResponse)
async def admin_recipes(request: Request, profile_id: int | None = None, q: str | None = None, include_archived: bool = False):
    """Sök och redigera recept."""
    active_profile_id = _resolve_profile(profile_id)
    query = q or ""
    if query:
        search_results = recipe_service.search_recipes(query, profile_id=active_profile_id, include_archived=include_archived)
    else:
        search_results = recipe_service.list_recipes(profile_id=active_profile_id, include_archived=include_archived)
    context = {
        "request": request,
        "title": "Hitta recept",
        "subtitle": "Sök och redigera recept",
        "search_query": query,
        "include_archived": include_archived,
        "search_results": search_results,
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("admin/recipes.html", context)


@router.get("/db", response_class=HTMLResponse)
async def admin_db(request: Request, profile_id: int | None = None):
    """Enkel inspektionssida för databasen med möjlighet att radera poster."""
    active_profile_id = _resolve_profile(profile_id)
    recipes = recipe_service.list_recipes(include_archived=True)  # alla profiler
    with connection_scope() as conn:
        menu_entries = conn.execute(
            "SELECT id, profile_id, day, week_number, year, recipe_id FROM menu_entries ORDER BY year DESC, week_number DESC, id DESC"
        ).fetchall()
        shopping_items = conn.execute(
            "SELECT id, profile_id, name, amount FROM shopping_items ORDER BY id DESC"
        ).fetchall()
    context = {
        "request": request,
        "title": "DB-inspektion",
        "subtitle": "Se rader och ta bort vid behov",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
        "recipes": recipes,
        "menu_entries": menu_entries,
        "shopping_items": shopping_items,
    }
    return templates.TemplateResponse("admin/db.html", context)


@router.get("/units", response_class=HTMLResponse)
async def admin_units(request: Request, profile_id: int | None = None):
    """Visa och förbered redigering av måttenheter."""
    active_profile_id = _resolve_profile(profile_id)
    units = get_all_units()
    categories = [
        (UnitCategory.WEIGHT, "Vikt"),
        (UnitCategory.VOLUME, "Volym"),
        (UnitCategory.SPOON, "Köksmått"),
        (UnitCategory.COUNT, "Styck"),
        (UnitCategory.OTHER, "Övrigt"),
    ]
    context = {
        "request": request,
        "title": "Måttenheter",
        "subtitle": "Redigera och planera mått och måttsatsangivelser",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
        "units": units,
        "categories": categories,
    }
    return templates.TemplateResponse("admin/units.html", context)


@router.get("/import", response_class=HTMLResponse)
async def admin_import_recipes(request: Request, profile_id: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    context = {
        "request": request,
        "title": "Importera recept",
        "subtitle": "Ladda upp en JSON-fil enligt importformatet",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
        "result": None,
    }
    return templates.TemplateResponse("admin/import_recipes.html", context)


@router.post("/import", response_class=HTMLResponse)
async def admin_import_recipes_post(
    request: Request,
    profile_id: int | None = Form(None),
    file: UploadFile = File(...),
):
    """Läs JSON med {\"recipes\": [...]} och skapa recept för vald profil."""
    active_profile_id = _resolve_profile(profile_id)
    content = await file.read()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ogiltig JSON-fil")

    # Stöd både för { "recipes": [...] } och ren list-root [...]
    if isinstance(payload, list):
        recipes_payload = payload
    elif isinstance(payload, dict):
        recipes_payload = payload.get("recipes", [])
    else:
        raise HTTPException(status_code=400, detail="Ogiltigt JSON-format")
    imported = 0
    for item in recipes_payload:
        title = item.get("title")
        if not title:
            continue
        description = item.get("description")
        servings_raw = item.get("servings")
        servings = None
        if isinstance(servings_raw, int):
            servings = servings_raw
        elif isinstance(servings_raw, str):
            try:
                servings = int(servings_raw)
            except ValueError:
                servings = None  # Tillåt t.ex. "3-4" utan att krascha
        created_by = item.get("created_by") or active_profile_id
        image_url = item.get("image_url")
        ingredients_payload = item.get("ingredients", [])
        steps_payload = item.get("steps", [])
        tags_payload = item.get("tags", [])

        ingredients = []
        for ing in ingredients_payload:
            name = ing.get("name")
            if not name:
                continue
            amount = ing.get("amount")
            ingredients.append(Ingredient(name=name, amount=amount))

        steps = [s for s in steps_payload if isinstance(s, str)]
        tags = [t for t in tags_payload if isinstance(t, str)]

        recipe_service.add_recipe(
            title=title,
            description=description,
            ingredients=ingredients,
            steps=steps,
            tags=tags,
            created_by=created_by,
            servings=servings,
            image_url=image_url,
            archived=bool(item.get("archived")) if isinstance(item, dict) else False,
        )
        imported += 1

    context = {
        "request": request,
        "title": "Importera recept",
        "subtitle": "Ladda upp en JSON-fil enligt importformatet",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
        "result": {"imported": imported, "total": len(recipes_payload)},
    }
    return templates.TemplateResponse("admin/import_recipes.html", context)


@router.get("/search")
async def admin_search_api(request: Request, profile_id: int | None = None, q: str = "", include_archived: bool = False):
    active_profile_id = _resolve_profile(profile_id)
    results = recipe_service.search_recipes(q, profile_id=active_profile_id, include_archived=include_archived)
    return JSONResponse({"results": [_serialize_recipe(r) for r in results]})


@router.post("/recipes/archive")
async def archive_recipe(
    recipe_id: int = Form(...),
    archived: int = Form(...),
    profile_id: int | None = Form(None),
):
    active_profile_id = _resolve_profile(profile_id)
    recipe_service.update_recipe(recipe_id, archived=bool(archived))
    return RedirectResponse(url=f"/admin/recipes?profile_id={active_profile_id}&include_archived=1", status_code=303)


@router.post("/db/delete-recipe")
async def admin_delete_recipe(recipe_id: int = Form(...), profile_id: int | None = Form(None)):
    active_profile_id = _resolve_profile(profile_id)
    with connection_scope() as conn:
        conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))
        conn.execute("DELETE FROM steps WHERE recipe_id = ?", (recipe_id,))
        conn.execute("DELETE FROM tags WHERE recipe_id = ?", (recipe_id,))
        conn.execute("DELETE FROM menu_entries WHERE recipe_id = ?", (recipe_id,))
        conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        conn.commit()
    return RedirectResponse(url=f"/admin/db?profile_id={active_profile_id}", status_code=303)


@router.post("/db/delete-menu-entry")
async def admin_delete_menu_entry(entry_id: int = Form(...), profile_id: int | None = Form(None)):
    active_profile_id = _resolve_profile(profile_id)
    with connection_scope() as conn:
        conn.execute("DELETE FROM menu_entries WHERE id = ?", (entry_id,))
        conn.commit()
    return RedirectResponse(url=f"/admin/db?profile_id={active_profile_id}", status_code=303)


@router.post("/db/delete-shopping-item")
async def admin_delete_shopping_item(item_id: int = Form(...), profile_id: int | None = Form(None)):
    active_profile_id = _resolve_profile(profile_id)
    with connection_scope() as conn:
        conn.execute("DELETE FROM shopping_items WHERE id = ?", (item_id,))
        conn.commit()
    return RedirectResponse(url=f"/admin/db?profile_id={active_profile_id}", status_code=303)


@router.get("/backup", response_class=FileResponse)
async def admin_backup(profile_id: int | None = None):
    """Skapa en zip-backup av databasen och bilderna och returnera för nedladdning."""
    _ = _resolve_profile(profile_id)
    db_path = settings.data_dir / "app.db"
    images_dir = settings.data_dir / "images"
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = backup_dir / f"backup-{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if db_path.exists():
            zf.write(db_path, arcname="app.db")
        if images_dir.exists():
            for path in images_dir.rglob("*"):
                if path.is_file():
                    arcname = Path("images") / path.relative_to(images_dir)
                    zf.write(path, arcname=str(arcname))

    return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)


@router.get("/edit", response_class=HTMLResponse)
async def admin_edit(request: Request, recipe_id: int, profile_id: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    recipe = recipe_service.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    context = {
        "request": request,
        "title": f"Redigera {recipe.title}",
        "recipe": recipe,
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("admin/edit.html", context)


@router.get("/profiles", response_class=HTMLResponse)
async def admin_profiles(request: Request, profile_id: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    context = {
        "request": request,
        "title": "Profiler",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile_service.get_profile(active_profile_id),
    }
    return templates.TemplateResponse("admin/profiles.html", context)


@router.get("/profile-settings", response_class=HTMLResponse)
async def admin_profile_settings(request: Request, profile_id: int | None = None):
    active_profile_id = _resolve_profile(profile_id)
    profile = profile_service.get_profile(active_profile_id)
    theme_options = [("auto", "System (auto)"), ("light", "Ljust läge"), ("dark", "Mörkt läge")]
    context = {
        "request": request,
        "title": "Profilinställningar",
        "subtitle": "Välj tema och profiluppgifter",
        "profiles": profile_service.list_profiles(),
        "current_profile": profile,
        "theme_options": theme_options,
    }
    return templates.TemplateResponse("admin/profile_settings.html", context)


@router.post("/profile-settings")
async def admin_profile_settings_post(
    request: Request,
    target_profile_id: int = Form(...),
    name: str | None = Form(None),
    email: str | None = Form(None),
    avatar_file: UploadFile | None = File(None),
    theme_preference: str | None = Form(None),
    profile_id: int | None = Form(None),
):
    active_profile_id = _resolve_profile(profile_id)
    saved_avatar: str | None = None
    if avatar_file and avatar_file.filename:
        images_dir = settings.data_dir / "images" / "avatars"
        images_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(avatar_file.filename).suffix
        filename = f"{uuid.uuid4().hex}{suffix}"
        target_path = images_dir / filename
        with target_path.open("wb") as f:
            f.write(await avatar_file.read())
        saved_avatar = f"/uploads/avatars/{filename}"
    profile_service.update_profile(
        target_profile_id,
        name=name or None,
        email=email or None,
        avatar_url=saved_avatar,
        theme_preference=theme_preference or None,
    )
    return RedirectResponse(url=f"/admin/profile-settings?profile_id={active_profile_id}", status_code=303)


@router.post("/profiles/new")
async def admin_profiles_new(
    request: Request,
    name: str = Form(...),
    email: str | None = Form(None),
    avatar_file: UploadFile | None = File(None),
    profile_id: int | None = Form(None),
):
    active_profile_id = _resolve_profile(profile_id)
    saved_avatar: str | None = None
    if avatar_file and avatar_file.filename:
        images_dir = settings.data_dir / "images" / "avatars"
        images_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(avatar_file.filename).suffix
        filename = f"{uuid.uuid4().hex}{suffix}"
        target_path = images_dir / filename
        with target_path.open("wb") as f:
            f.write(await avatar_file.read())
        saved_avatar = f"/uploads/avatars/{filename}"
    profile_service.create_profile(name=name, email=email or None, avatar_url=saved_avatar)
    return RedirectResponse(
        url=f"/admin/profiles?profile_id={active_profile_id}",
        status_code=303,
    )


@router.post("/profiles/update")
async def admin_profiles_update(
    request: Request,
    target_profile_id: int = Form(...),
    name: str = Form(...),
    email: str | None = Form(None),
    avatar_file: UploadFile | None = File(None),
    profile_id: int | None = Form(None),
):
    active_profile_id = _resolve_profile(profile_id)
    saved_avatar: str | None = None
    if avatar_file and avatar_file.filename:
        images_dir = settings.data_dir / "images" / "avatars"
        images_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(avatar_file.filename).suffix
        filename = f"{uuid.uuid4().hex}{suffix}"
        target_path = images_dir / filename
        with target_path.open("wb") as f:
            f.write(await avatar_file.read())
        saved_avatar = f"/uploads/avatars/{filename}"
    updated = profile_service.update_profile(
        target_profile_id,
        name=name,
        email=email or None,
        avatar_url=saved_avatar,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return RedirectResponse(
        url=f"/admin/profiles?profile_id={active_profile_id}",
        status_code=303,
    )


@router.post("/edit")
async def admin_edit_post(
    request: Request,
    recipe_id: int = Form(...),
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
    recipe = recipe_service.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    servings_value: int | None = None
    if servings:
        try:
            servings_value = int(servings)
        except ValueError:
            servings_value = None

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

    ingredients = []
    for line in ingredients_text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        parts = clean.split(" ", 1)
        amount = parts[0] if len(parts) > 1 else None
        name = parts[1] if len(parts) > 1 else parts[0]
        ingredients.append(Ingredient(name=name, amount=amount))

    steps = [s.strip() for s in steps_text.splitlines() if s.strip()]
    tags = [t.strip() for t in tags_text.split(",") if t.strip()]

    recipe_service.update_recipe(
        recipe_id,
        title=title,
        description=description,
        servings=servings_value,
        ingredients=ingredients,
        steps=steps,
        tags=tags,
        image_url=uploaded_url or image_url or recipe.image_url,
    )

    return RedirectResponse(
        url=f"/recipes/{recipe_id}?profile_id={active_profile_id}",
        status_code=303,
    )
