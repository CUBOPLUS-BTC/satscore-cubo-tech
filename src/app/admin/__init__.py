"""
Admin module for Magma Bitcoin app.
Provides dashboard analytics, user management, and system administration.
"""

from .dashboard import AdminDashboard
from .users import UserManager
from .system import SystemAdmin

__all__ = ["AdminDashboard", "UserManager", "SystemAdmin"]
