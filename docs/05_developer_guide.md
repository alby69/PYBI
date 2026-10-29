# 🛠️ PyBI Developer Guide

## 1. Setup & Environment
PyBI uses Python 3.10+ and standard Python virtual environments or Poetry.

### Local Setup
```bash
# Clone repository
git clone https://github.com/alby69/PYBI.git
cd PYBI

# Install editable package & dependencies
pip install -e .
```

---

## 2. Running Tests
Run tests using `pytest`:

```bash
python3 -m pytest
```

---

## 3. Extending the DAX Engine
To add a new DAX function (e.g. `PRODUCT`), use the `@DaxEngine.register` decorator in `backend/core/dax_engine/translator.py`:

```python
from backend.core.dax_engine import DaxEngine

@DaxEngine.register("PRODUCT")
def _translate_product(args, model=None):
    if not args:
        raise ValueError("PRODUCT requires at least 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"PRODUCT({arg})"
```

---

## 4. Running the Development Server
```bash
python3 -m pybi.main
```
Or start backend REST API directly:
```bash
python3 -m backend.main
```
