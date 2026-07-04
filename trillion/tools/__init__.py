"""Trillion's hands. Adding a capability = write one tool module, register it
here. The core loop never changes."""

from .registry import Registry, Tool


def build_default_registry(config) -> Registry:
    from . import dashboard, focus, web

    registry = Registry()
    for module in (focus, dashboard, web):
        for tool in module.TOOLS:
            registry.register(tool)
    return registry
