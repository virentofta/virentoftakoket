# Virentoftakoket

En enkel FastAPI-baserad app för recept, veckomenyer och inköpslistor. Strukturen är förberedd för mallar, statiska filer och SQLite-lagring. Starta med att aktivera `.venv` och köra `uvicorn app:app --reload` när logiken är på plats.

## Struktur
- `app.py` – startpunkt för FastAPI och router-registrering.
- `core/` – konfiguration och databaskoppling.
- `models/` – pydantic-/dataklasser för recept, menyer och inköpslistor.
- `models/profile.py` – profil för att knyta recept/menyer/listor till en användare (ingen auth).
- `routes/` – endpoints för sidor, recept och adminimport.
- `services/` – affärslogik och beräkningar.
- `templates/` – Jinja2-mallar för HTML-sidor.
- `static/` – CSS och JS.
- `data/` – SQLite-databas och bilder (ignored av git).
- Förifyllda profiler (utan auth): Per, Marika, Sally och Jack. Välj profil via hemsidan för att filtrera recept/menyer/listor.

## Nästa steg
- Lägg till verkliga modeller och databaslogik i `models/` och `core/database.py`.
- Koppla affärslogik i `services/` och använd den i routarna.
- Fyll på mallar och CSS med riktigt innehåll.
