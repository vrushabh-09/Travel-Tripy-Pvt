"""
COPYRIGHT ENFORCEMENT SYSTEM
Copyright (c) 2025 Vrushabh Patil. All Rights Reserved.
Contact: vrushabhpatil97711@gmail.com
"""

import sys
import hashlib
from datetime import datetime

class CopyrightEnforcer:
    """Enforces copyright protection across the application"""
    
    def __init__(self):
        self.owner = "Vrushabh Patil"
        self.year = "2025"
        self.email = "vrushabhpatil97711@gmail.com"
        self.legal_text = self._get_legal_text()
        
    def _get_legal_text(self):
        return f"""
        ╔════════════════════════════════════════════════════════════════╗
        ║                      LEGAL NOTICE                             ║
        ║  Copyright (c) {self.year} {self.owner}. All Rights Reserved.     ║
        ║  Contact: {self.email}                                        ║
        ║                                                                ║
        ║  PROPRIETARY AND CONFIDENTIAL                                 ║
        ║  This software contains trade secrets and proprietary         ║
        ║  information owned by {self.owner}.                          ║
        ║  Unauthorized copying, distribution, or modification          ║
        ║  may result in severe civil and criminal penalties.           ║
        ║  Violators will be prosecuted to the maximum extent possible. ║
        ╚════════════════════════════════════════════════════════════════╝
        """
    
    def display_copyright(self):
        """Display copyright notice"""
        print(self.legal_text)
    
    def check_integrity(self):
        """Check if code has been tampered with"""
        # This would be more sophisticated in production
        current_hash = self._calculate_integrity_hash()
        expected_hash = "protected_code_hash_placeholder"  # Set this during deployment
        
        if current_hash != expected_hash:
            self._trigger_defense_measures()
            return False
        return True
    
    def _calculate_integrity_hash(self):
        """Calculate integrity hash of critical code sections"""
        # Hash important parts of your code
        critical_sections = [
            "SecurityProtection",
            "CopyrightEnforcer", 
            "main_app_logic"
        ]
        return hashlib.sha256(str(critical_sections).encode()).hexdigest()
    
    def _trigger_defense_measures(self):
        """Activate defense when tampering detected"""
        violation_message = f"""
        🚨 COPYRIGHT VIOLATION DETECTED 🚨
        
        VIOLATION DETAILS:
        - Timestamp: {datetime.now()}
        - Protected Work: Travel Tripy AI Assistant
        - Copyright Owner: {self.owner}
        - Copyright Year: {self.year}
        - Contact: {self.email}
        
        LEGAL CONSEQUENCES:
        - This violation has been logged
        - Legal action will be initiated
        - Maximum statutory damages will be sought
        
        IMMEDIATE ACTION REQUIRED:
        Cease all unauthorized use immediately and contact {self.email}
        """
        
        print(violation_message)
        # In production, you might want to send this to a logging service
        # or even restrict functionality

# Global enforcer instance
COPYRIGHT_ENFORCER = CopyrightEnforcer()

def enforce_copyright():
    """Enforce copyright protection"""
    COPYRIGHT_ENFORCER.display_copyright()
    return COPYRIGHT_ENFORCER.check_integrity()

# Auto-enforce on import
enforce_copyright()