import importlib
import sys
import warnings


def test_backend_root_is_deprecated():
    sys.modules.pop("backend", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        backend = importlib.import_module("backend")

    assert backend.__version__
    assert any("deprecated" in str(warning.message).lower() for warning in caught)


def test_legacy_backend_main_exports_api_app():
    module = importlib.import_module("backend.main")
    assert module.app is not None
