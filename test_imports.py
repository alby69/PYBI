import sys

libs = [
    "polars",
    "pyarrow", 
    "duckdb",
    "pandas",
    "numpy",
    "nicegui",
    "fastapi",
    "uvicorn",
    "pydantic",
    "sqlalchemy",
    "casbin",
    "ibis_framework",
    "sqlglot",
    "weasyprint",
    "jinja2",
    "yaml",
    "pydantic_settings"
]

for lib in libs:
    try:
        print(f"Testing {lib}...", end=" ")
        __import__(lib)
        print("✓ OK")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        sys.exit(1)

print("\nTutte le librerie importate con successo!")
