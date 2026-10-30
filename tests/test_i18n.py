from fastapi.testclient import TestClient

from pybi.api.main import create_app


client = TestClient(create_app())


def test_locale_catalog_endpoint_returns_supported_catalogs():
    for locale, expected in (("it", "Passaggi applicati"), ("en", "Applied Steps")):
        response = client.get(f"/api/v1/locales/{locale}", headers={"Accept-Language": locale})
        assert response.status_code == 200
        assert response.headers["content-language"] == locale
        assert response.json()["etl"]["appliedSteps"] == expected

    assert client.get("/api/v1/locales/fr").status_code == 404


def test_locale_negotiation_uses_quality_and_saved_locale_cookie():
    response = client.get(
        "/api/v1/locales/en",
        headers={"Accept-Language": "fr-FR, en-US;q=0.8, it;q=0.4"},
    )
    assert response.headers["content-language"] == "en"

    response = client.get(
        "/api/v1/locales/it",
        headers={"Accept-Language": "en-US", "Cookie": "pybi_locale=it-IT"},
    )
    assert response.headers["content-language"] == "it"


def test_validation_details_follow_requested_language():
    url = "/api/v1/projects/demo/report/tables/sales/values"
    english = client.get(url, headers={"Accept-Language": "en-US"})
    italian = client.get(url, headers={"Accept-Language": "it-IT"})

    assert english.status_code == italian.status_code == 422
    assert english.json()["detail"][0]["msg"] == "Field required"
    assert italian.json()["detail"][0]["msg"] == "Campo obbligatorio"


def test_locale_store_and_selector_are_registered():
    from pybi.ui.components import report_registry

    assert report_registry.LanguageSelector.component is not None
    assert report_registry.LanguageSelector.component.tag == "nicegui-LanguageSelector"