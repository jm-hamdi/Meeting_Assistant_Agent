"""Tool registry — auto-discovers all @tool functions and Tool subclasses."""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil

from smolagents.tools import Tool

logger = logging.getLogger("meet_assistant.tools")


def discover_tools(package_name: str = "meet_assistant.tools") -> list[Tool]:
    """Scan all submodules of *package_name* and collect every smolagents Tool."""
    tools: list[Tool] = []
    seen_names: set[str] = set()

    try:
        package = importlib.import_module(package_name)
    except Exception as exc:
        logger.error("Failed to import package %s: %s", package_name, exc)
        return tools

    package_path = getattr(package, "__path__", None)
    if not package_path:
        return tools

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        if module_name.startswith("_"):
            continue

        full_name = f"{package_name}.{module_name}"
        try:
            mod = importlib.import_module(full_name)
            for attr_name in dir(mod):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(mod, attr_name)

                if isinstance(attr, Tool):
                    if attr.name not in seen_names:
                        seen_names.add(attr.name)
                        tools.append(attr)
                        logger.debug("Registered tool instance: %s (%s)", attr.name, full_name)

                elif inspect.isclass(attr) and issubclass(attr, Tool) and attr is not Tool:
                    try:
                        instance = attr()
                        if instance.name not in seen_names:
                            seen_names.add(instance.name)
                            tools.append(instance)
                            logger.debug("Registered tool class: %s (%s)", instance.name, full_name)
                    except Exception as inst_exc:
                        logger.warning("Could not instantiate tool class %s: %s", attr_name, inst_exc)

        except Exception as exc:
            logger.error("Error loading tools from %s: %s", full_name, exc)

    return tools
