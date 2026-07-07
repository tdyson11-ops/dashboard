"""Trillion's hands. Adding a capability = write one tool module, register it
here. The core loop never changes."""

from .registry import Registry, Tool


def build_default_registry(config, memory=None) -> Registry:
    from . import comms, dashboard, focus, web

    registry = Registry()
    for module in (focus, dashboard, web, comms):
        for tool in module.TOOLS:
            registry.register(tool)
    if memory is not None:
        from .memory_tools import build_memory_tools

        for tool in build_memory_tools(memory):
            registry.register(tool)
    return registry
