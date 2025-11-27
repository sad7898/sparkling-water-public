"""
Provides utilities for storing data in S3 for the cryptocurrency sentiment analysis project.
"""

__version__ = "0.1.0"

from .save_to_s3 import save_to_s3

__all__ = ["save_to_s3"]