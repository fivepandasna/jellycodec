"""jellycodec package

Expose package version and CLI entrypoint for packaging.
"""

__version__ = "0.1.0"

from .__main__ import main, JellyfinCodecAnalyzer

__all__ = ["main", "JellyfinCodecAnalyzer", "__version__"]
