"""Drill-Through Engine for managing navigation history and forced filter contexts."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class DrillEngine:
    """Manages drill-through navigation stack and filter context inheritance."""

    def __init__(self) -> None:
        self.drill_context: Optional[Dict[str, Any]] = None
        self.drill_history: List[Dict[str, Any]] = []

    def set_drill_context(self, target_report: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Push current context onto history stack and set active drill context."""
        if self.drill_context:
            self.drill_history.append({
                "drill_context": dict(self.drill_context),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        self.drill_context = {
            "target_report": target_report,
            "filters": dict(filters),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self.drill_context

    def pop_drill_context(self) -> Optional[Dict[str, Any]]:
        """Pop previous drill state from navigation history stack."""
        if self.drill_history:
            prev = self.drill_history.pop()
            self.drill_context = prev.get("drill_context")
            return self.drill_context
        else:
            self.drill_context = None
            return None

    def clear(self) -> None:
        """Clear all active drill contexts and history."""
        self.drill_context = None
        self.drill_history.clear()


default_drill_engine = DrillEngine()
