# -*- coding: utf-8 -*-
"""
    Resource path utilities for Qt6 compatibility
"""

import os


def resources_path(*args) -> str:
    """Get the path to plugin resources folder.

    Note: In Qt6 compatibility update, we removed the use of Qt Resource files
    in favour of directly accessing on-disk resources.

    Args:
        *args: List of path elements e.g. ['icons', 'icon.svg']

    Returns:
        str: Absolute path to the resources folder or file.

    Example:
        >>> resources_path("icons", "icon.svg")
        '/path/to/cplus_plugin/icons/icon.svg'
    """
    # Get the parent directory (cplus_plugin/)
    path = os.path.dirname(os.path.dirname(__file__))
    path = os.path.abspath(path)
    for item in args:
        path = os.path.abspath(os.path.join(path, item))
    return path
