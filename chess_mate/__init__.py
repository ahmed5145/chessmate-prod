"""
ChessMate - Chess Analysis and Improvement Platform
"""

import builtins
import sys

__version__ = "1.0.0"

# Legacy test compatibility: some older tests reference `chess_mate` directly
# without importing it first.
builtins.chess_mate = sys.modules[__name__]

try:
	import core as _core
	import core.redis_config as _redis_config

	core = _core
	sys.modules.setdefault("chess_mate.core", _core)
	sys.modules.setdefault("chess_mate.core.redis_config", _redis_config)
except Exception:
	pass
