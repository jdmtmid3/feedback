"""
License Manager Module
Handles license validation, key verification, and expiry checks for the feedback system.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LicenseManager:
    """Manages license validation and verification."""
    
    def __init__(self):
        self.current_license = None
    
    def generate_license_key(self) -> str:
        """Generate a new unique license key."""
        return secrets.token_urlsafe(32)
    
    def hash_license_key(self, license_key: str) -> str:
        """Hash a license key for storage."""
        return hashlib.sha256(license_key.encode()).hexdigest()
    
    def validate_license_key_format(self, license_key: str) -> bool:
        """Validate that a license key has the correct format."""
        if not license_key or len(license_key) < 16:
            return False
        return True
    
    def is_license_expired(self, expiry_date: Optional[datetime]) -> bool:
        """Check if a license has expired."""
        if expiry_date is None:
            return False  # No expiry means perpetual
        # Compare date parts if expiry_date is a date object
        if isinstance(expiry_date, date) and not isinstance(expiry_date, datetime):
            return datetime.now().date() > expiry_date
        return datetime.now() > expiry_date
    
    def check_feature_enabled(self, features: Dict[str, bool], feature_name: str) -> bool:
        """Check if a specific feature is enabled in the license."""
        return features.get(feature_name, False)
    
    def get_license_status(self, license_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get comprehensive license status."""
        if not license_data:
            return {
                "valid": False,
                "active": False,
                "expired": False,
                "message": "No license configured",
                "features": {}
            }
        
        expiry_date = license_data.get("expiry_date")
        is_expired = self.is_license_expired(expiry_date)
        is_active = license_data.get("is_active", False)
        
        status = {
            "valid": is_active and not is_expired,
            "active": is_active,
            "expired": is_expired,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "message": "License active" if (is_active and not is_expired) else ("License expired" if is_expired else "License inactive"),
            "features": license_data.get("features", {}),
            "max_stores": license_data.get("max_stores", 0),
            "max_questionnaires": license_data.get("max_questionnaires", 0)
        }
        
        return status


# Global license manager instance
license_manager = LicenseManager()
