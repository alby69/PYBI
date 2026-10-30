"""Report View data models (pages, canvas visuals, filters and layout).

These models mirror the structures used by the PYBI Vue report editor and the
Power BI Desktop report canvas.  They are intentionally permissive on the
``properties`` / ``data_buckets`` dictionaries so that new visual formatting
options can be introduced without a backend migration.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


PAGE_PRESETS: Dict[str, Dict[str, int]] = {
    "16:9": {"width": 1280, "height": 720},
    "4:3": {"width": 960, "height": 720},
    "tooltip": {"width": 320, "height": 240},
}
DEFAULT_PAGE_WIDTH = 1280
DEFAULT_PAGE_HEIGHT = 720


def generate_id(prefix: str) -> str:
    """Return a short unique identifier with the given prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class VisualPosition(BaseModel):
    """Position and size of a visual on the report canvas (pixels)."""

    x: int = Field(0, description="Posizione X sul canvas in pixel")
    y: int = Field(0, description="Posizione Y sul canvas in pixel")
    width: int = Field(400, description="Larghezza in pixel")
    height: int = Field(260, description="Altezza in pixel")
    z_index: int = Field(1, description="Livello di sovrapposizione")


class VisualWidget(BaseModel):
    """A single visual (chart, table, card, slicer, ...) on a report page."""

    id: str = Field(default_factory=lambda: generate_id("vis"), description="ID univoco del visual")
    type: str = Field(
        "bar_chart",
        description="Tipo visuale (bar_chart, line_chart, pie_chart, table, card, slicer, etc.)",
    )
    title: str = Field("Titolo Visual", description="Titolo visualizzato")
    position: VisualPosition = Field(default_factory=VisualPosition)
    data_buckets: Dict[str, Any] = Field(
        default_factory=dict,
        description="Mappatura campi (X-Axis, Y-Axis, Legend, Values)",
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Proprietà di formattazione (colors, font, background, etc.)",
    )
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Filtri a livello di singolo visual")

    def duplicate(self, offset: int = 24) -> "VisualWidget":
        """Return a deep copy of the visual with a new id and a small offset."""
        clone = self.model_copy(deep=True)
        clone.id = generate_id("vis")
        clone.position.x = max(0, clone.position.x + offset)
        clone.position.y = max(0, clone.position.y + offset)
        return clone


class ReportPage(BaseModel):
    """A report page containing a set of visuals."""

    id: str = Field(default_factory=lambda: generate_id("page"))
    name: str = "Pagina 1"
    is_hidden: bool = False
    page_type: str = Field("Standard", description="Standard, Tooltip or Drillthrough")
    width: int = DEFAULT_PAGE_WIDTH
    height: int = DEFAULT_PAGE_HEIGHT
    visuals: List[VisualWidget] = Field(default_factory=list)
    page_filters: List[Dict[str, Any]] = Field(default_factory=list)
    background: Optional[str] = None
    wallpaper: Optional[str] = None

    def duplicate(self) -> "ReportPage":
        """Return a deep copy of the page with new ids for page and visuals."""
        clone = self.model_copy(deep=True)
        clone.id = generate_id("page")
        clone.name = f"{self.name} (copia)"
        clone.visuals = [visual.duplicate(offset=0) for visual in self.visuals]
        return clone


class ReportLayout(BaseModel):
    """Root report document: ordered pages, report filters and active page."""

    project_id: str = "default"
    active_page_id: str = Field(default_factory=lambda: generate_id("page"))
    pages: List[ReportPage] = Field(default_factory=list)
    report_filters: List[Dict[str, Any]] = Field(default_factory=list)
    theme: str = "PowerBI_Classic"

    @classmethod
    def create_default(cls, project_id: str = "default", theme: str = "PowerBI_Classic") -> "ReportLayout":
        """Create a report with one empty standard page."""
        page = ReportPage(id=generate_id("page"))
        return cls(
            project_id=project_id,
            active_page_id=page.id,
            pages=[page],
            report_filters=[],
            theme=theme,
        )

    def get_page(self, page_id: Optional[str]) -> Optional[ReportPage]:
        """Return a page by id, or the active page when no id is provided."""
        target = page_id or self.active_page_id
        for page in self.pages:
            if page.id == target:
                return page
        return self.pages[0] if self.pages else None

    def ensure_valid_state(self) -> "ReportLayout":
        """Guarantee that at least one page exists and active_page_id is valid."""
        if not self.pages:
            self.pages = [ReportPage()]
        if not any(page.id == self.active_page_id for page in self.pages):
            self.active_page_id = self.pages[0].id
        return self


__all__ = [
    "DEFAULT_PAGE_HEIGHT",
    "DEFAULT_PAGE_WIDTH",
    "PAGE_PRESETS",
    "ReportLayout",
    "ReportPage",
    "VisualPosition",
    "VisualWidget",
    "generate_id",
]
