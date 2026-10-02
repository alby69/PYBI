"""Guard tests keeping declared dependencies in sync with the code.

The project lists its dependencies twice (requirements.txt, used by the
Dockerfile, and pyproject.toml). They drifted in the past: pyarrow and then
sqlalchemy were imported by the code but missing from requirements.txt, so the
Docker image could not even import pybi.etl and /etl-editor returned HTTP 500.
"""

import ast
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Modules provided by the standard library or by the project itself.
STDLIB_AND_LOCAL = {
    'abc', 'ast', 'asyncio', 'collections', 'contextlib', 'copy', 'csv', 'dataclasses',
    'datetime', 'functools', 'graphlib', 'hashlib', 'io', 'itertools', 'json', 'logging',
    'math', 'os', 'pathlib', 'random', 're', 'socket', 'sqlite3', 'string', 'subprocess',
    'sys', 'tempfile', 'textwrap', 'time', 'traceback', 'typing', 'unittest', 'urllib', 'uuid',
    'pybi',
}


def declared_requirements():
    """Parse top-level distribution names from requirements.txt."""
    names = set()
    for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        match = re.match(r'([A-Za-z0-9_.-]+)', line)
        if match:
            names.add(match.group(1).lower().replace('_', '-'))
    return names


def declared_pyproject():
    """Parse dependency names from the pyproject.toml project.dependencies list."""
    text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    block = re.search(r'^dependencies\s*=\s*\[(.*?)\]', text, re.MULTILINE | re.DOTALL)
    assert block, 'No dependencies list found in pyproject.toml'
    return {
        match.group(1).lower().replace('_', '-')
        for match in re.finditer(r'["\']([A-Za-z0-9_.-]+)\s*[><=!~]', block.group(1))
    }


def imported_top_level_modules():
    """Collect top-level modules imported by the pybi package."""
    modules = set()
    for path in (ROOT / 'pybi').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    modules.add(node.module.split('.')[0])
    return modules - STDLIB_AND_LOCAL


@pytest.mark.parametrize('module', sorted(imported_top_level_modules()))
def test_imported_module_is_declared_in_requirements(module):
    """Every third-party import must be installable from requirements.txt."""
    normalized = module.lower().replace('_', '-')
    assert normalized in declared_requirements(), (
        f"'{module}' is imported by pybi but missing from requirements.txt: "
        f"the Docker image would fail to import it."
    )


@pytest.mark.parametrize('module', sorted(imported_top_level_modules()))
def test_imported_module_is_declared_in_pyproject(module):
    """Every third-party import must also be declared in pyproject.toml."""
    normalized = module.lower().replace('_', '-')
    assert normalized in declared_pyproject(), (
        f"'{module}' is imported by pybi but missing from pyproject.toml dependencies."
    )


def test_requirements_and_pyproject_declare_the_same_packages():
    """requirements.txt and pyproject.toml must not drift apart."""
    assert declared_requirements() == declared_pyproject()


def test_etl_connectors_are_importable():
    """Every connector must import with the declared dependencies installed.

    pybi.etl.connectors imports its connectors eagerly, so a single missing
    dependency breaks the whole ETL package and makes /etl-editor return HTTP
    500 in Docker.
    """
    import importlib

    for module in ('pybi.etl.connectors', 'pybi.etl.connectors.csv',
                   'pybi.etl.connectors.parquet', 'pybi.etl.connectors.sqlite',
                   'pybi.etl.connectors.postgres'):
        importlib.import_module(module)


def test_pages_are_importable():
    """UI page modules must import, so a bad import fails tests instead of the page."""
    import importlib

    for module in ('pybi.main', 'pybi.ui.pages.etl_editor',
                   'pybi.ui.pages.dashboard_editor', 'pybi.ui.pages.viewer'):
        importlib.import_module(module)
