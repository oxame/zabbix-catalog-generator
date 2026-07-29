"""Catalogue generator compatibility module.

The implementation remains in :mod:`zabbix_catalog_generator.excel` during the
incremental generator refactor. Importing it here establishes the public
``generators`` namespace without breaking existing callers.
"""

from ..excel import generate_catalogue

__all__ = ["generate_catalogue"]
