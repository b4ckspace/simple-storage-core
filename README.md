# simple-storage-core

Terminal-based storage manager focused on local inventory workflows.

License: [MIT](LICENSE)

## Scope

- Create products (`SKU`, `Name`, `Qty`, `Shelf`, `Bin`, `Slot`)
- Search by name, SKU, and barcode/GTIN
- Edit quantity and location
- Inventory session (start, count, export, apply)
- Brother-QL label printing
- Local-first operation with SQLite by default
- Optional PostgreSQL backend

## Project Files

- [lager_mc.py](lager_mc.py): main TUI app
- [label_print.py](label_print.py): label generation/printing
- [storage_db.py](storage_db.py): DB backend abstraction (`sqlite` / `postgres`)
- [app_settings.py](app_settings.py): default + local settings loader
- [settings.json](settings.json): versioned base settings

## Requirements

- Python 3.11+
- `curses`
- Label print stack: `Pillow`, `python-barcode`, `brother-ql`
- Optional PostgreSQL adapter: `psycopg2-binary`

Install:

```bash
git clone <repo-url>
cd simple-storage-core
./scripts/install-linux.sh
```

## Configuration

Settings are loaded from:

- `settings.json` (project defaults, versioned)
- `settings.local.json` (local overrides, not versioned)

Important keys:

- `db_backend`: `sqlite` or `postgres`
- `sqlite_path`: path to SQLite file
- `db_host`, `db_name`, `db_user`, `db_pass`: PostgreSQL connection
- `language`: `en` or `de`
- `color_theme`, `color_theme_file`
- `printer_uri`, `printer_model`, `label_size`
- `label_font_regular`, `label_font_condensed`
- `location_regex_regal`, `location_regex_fach`, `location_regex_platz`

## Run

```bash
python3 lager_mc.py
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```
