"""
Bridge package: NX CAD adapter for gesture-based viewport control.

Provides the NXBridge class for translating abstract gesture commands
into NX Open API viewport operations.
"""

from .nx_bridge import NXBridge, CommandType, CommandDispatcher

__all__ = ["NXBridge", "CommandType", "CommandDispatcher"]
