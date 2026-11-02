"""Compatibility exports for the canonical ETL API."""

from pybi.api.v1 import etl as _canonical
from pybi.api.v1.etl import *
from pybi.api.v1.etl import (
    get_etl_query as get_etl_dag,
    preview_etl_step as preview_node_output,
    save_etl_query as save_etl_dag,
)
from pybi.api.v1.models import ETLExecuteResponse, ETLPreviewResponse
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import ETLExecutor


def __getattr__(name: str):
    return getattr(_canonical, name)
