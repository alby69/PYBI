# PyBI Developer Guide

## 1. Setup and Environment

PyBI supports Python 3.10+.

```bash
git clone https://github.com/alby69/PYBI.git
cd PYBI
pip install -e ".[test]"
cp .env.example .env
```

For local development, set `DATA_DIR=pybi_data` in `.env`; the example's
`/app/data` path is intended for Docker.

For browser-based UI tests, install Chromium once:

```bash
playwright install --with-deps chromium
```

Set `PYBI_JWT_SECRET` to a random value of at least 32 characters and
`PYBI_ENV=production` in production. Without a configured secret, local
development uses a randomly generated, process-local key.

## 2. Running Tests

```bash
python -m pytest
```

## 3. Extending the DAX Engine

Add DAX translations in `pybi/semantic/dax_translator.py`:

```python
from pybi.semantic.dax_translator import DaxEngine


@DaxEngine.register("PRODUCT")
def _translate_product(args, model=None):
    if not args:
        raise ValueError("PRODUCT requires at least 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"PRODUCT({arg})"
```

## 4. Module Placement

- API DTOs and routes belong in `pybi.api`.
- Persisted semantic definitions, DAX, relationships, RLS, and synchronization
  belong in `pybi.semantic`.
- Dashboard cross-filter state belongs in `pybi.dashboard.filter_context`.
- Report-specific layout and rendering belong in `pybi.report`; report visuals
  consume the dashboard's shared filter context.
- Low-level shared primitives belong in `pybi.core`. Publish cross-module
  notifications with `pybi.core.events.event_bus` rather than importing a
  consumer module into ETL.
- Prefer `pybi.semantic.*` and `pybi.report.*`; `pybi.model` and `pybi.models`
  are re-export compatibility packages.
- `backend` is deprecated. Its former subpackage imports are removed;
  `python -m backend.main` remains only as a launch wrapper.

Before adding a new module, check whether an existing canonical module already
owns that responsibility and add a focused test for its public contract.

## 5. Running the Development Server

```bash
python -m pybi.main
```

The deprecated REST-only launch wrapper remains available:

```bash
python -m backend.main
```
