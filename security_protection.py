"""
HIGH-LEVEL SECURITY PROTECTION SYSTEM
Copyright (c) 2025 Vrushabh Patil. All Rights Reserved.
Contact: vrushabhpatil97711@gmail.com
PROPRIETARY CODE - DO NOT COPY OR DISTRIBUTE
"""

import hashlib
import inspect
import sys
import os
from datetime import datetime
import warnings

class SecurityProtection:
    """
    Advanced Code Protection System
    Prevents unauthorized copying and distribution
    """
    
    def __init__(self):
        self.owner = "Vrushabh Patil"
        self.copyright = "2025"
        self.email = "vrushabhpatil97711@gmail.com"
        self.license = "PROPRIETARY"
        self.creation_date = "2025-01-01"
        self.code_signature = self._generate_code_signature()
        self.fingerprint = self._generate_digital_fingerprint()
        
    def _generate_code_signature(self):
        """Generate unique signature based on code content"""
        caller_frame = inspect.currentframe().f_back.f_back
        source_code = ""
        try:
            source_code = inspect.getsource(caller_frame)
        except:
            # Get current file content as fallback
            current_file = __file__
            with open(current_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        
        signature = hashlib.sha256(f"{source_code}{self.owner}{self.copyright}".encode()).hexdigest()
        return signature
    
    def _generate_digital_fingerprint(self):
        """Create digital fingerprint of the application"""
        fingerprint_data = {
            'owner': self.owner,
            'copyright': self.copyright,
            'timestamp': datetime.now().isoformat(),
            'system_id': hashlib.md5(str(os.getpid()).encode()).hexdigest()
        }
        return hashlib.sha256(str(fingerprint_data).encode()).hexdigest()
    
    def verify_ownership(self):
        """Verify code integrity and ownership"""
        current_signature = self._generate_code_signature()
        
        if current_signature != self.code_signature:
            self._trigger_protection_measures()
            return False
        
        self._display_copyright_warning()
        return True
    
    def _trigger_protection_measures(self):
        """Activate protection when tampering detected"""
        warnings.warn(
            "🚨 SECURITY VIOLATION: Unauthorized code modification detected! "
            "Copyright (c) 2025 Vrushabh Patil. All Rights Reserved. "
            "Contact: vrushabhpatil97711@gmail.com",
            UserWarning,
            stacklevel=3
        )
        
        # Log the violation
        violation_msg = f"""
        ⚠️ COPYRIGHT VIOLATION DETECTED ⚠️
        Timestamp: {datetime.now()}
        Owner: {self.owner}
        Copyright: {self.copyright}
        Contact: {self.email}
        Action: Legal measures will be pursued
        """
        print(violation_msg)
    
    def _display_copyright_warning(self):
        """Display copyright notice on execution"""
        copyright_banner = f"""
        🔒 PROPRIETARY CODE PROTECTION SYSTEM 🔒
        ========================================
        Application: Travel Tripy AI Assistant
        Copyright (c) {self.copyright} {self.owner}
        All Rights Reserved
        Contact: {self.email}
        License: {self.license}
        
        ⚠️  WARNING: This code is protected by copyright law.
        ⚠️  Unauthorized copying, distribution, or modification is strictly prohibited.
        ⚠️  Legal action will be taken against violations.
        
        Digital Fingerprint: {self.fingerprint[:16]}...
        ========================================
        """
        print(copyright_banner)
    
    def get_legal_notice(self):
        """Return legal notice for display"""
        return f"""
        LEGAL NOTICE:
        © {self.copyright} {self.owner}. All Rights Reserved.
        This software is proprietary and confidential.
        Unauthorized copying, distribution, or modification is prohibited.
        Contact: {self.email}
        """
    
    def generate_watermark(self, content):
        """Add digital watermark to content"""
        watermark = f"©{self.copyright}{self.owner}"
        watermarked_content = f"{content}\n\n<!-- {watermark} -->"
        return watermarked_content

# Global security instance
SECURITY_GUARD = SecurityProtection()

def protect_code():
    """Main protection function to call in your app"""
    return SECURITY_GUARD.verify_ownership()

def get_copyright_notice():
    """Get copyright notice for display in UI"""
    return SECURITY_GUARD.get_legal_notice()

def add_watermark(text):
    """Add watermark to text content"""
    return SECURITY_GUARD.generate_watermark(text)

# Auto-execute protection when imported
if protect_code():
    print("✅ Security system activated - Code protection enabled")
else:
    print("🚨 Security violation detected - Protection measures activated")