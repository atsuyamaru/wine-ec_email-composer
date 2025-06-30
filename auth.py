import streamlit as st
import hashlib
import hmac
from typing import Dict, Optional

class StreamlitAuth:
    """Simple authentication system for Streamlit apps."""
    
    def __init__(self):
        # Initialize session state for authentication
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'username' not in st.session_state:
            st.session_state.username = None
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get credentials from Streamlit secrets or fallback to default."""
        try:
            # Try to get credentials from Streamlit secrets (for production)
            return st.secrets["credentials"]
        except (KeyError, FileNotFoundError):
            # Fallback for local development
            return {
                "admin": "password123",  # Change this for production!
                "demo": "demo123"
            }
    
    def _hash_password(self, password: str, salt: str = "wine_app_salt") -> str:
        """Hash password with salt for secure comparison."""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _verify_password(self, username: str, password: str) -> bool:
        """Verify username and password."""
        credentials = self._get_credentials()
        
        if username not in credentials:
            return False
        
        # For simplicity, we're doing direct comparison
        # In production, you should hash the stored passwords too
        return credentials[username] == password
    
    def login_form(self) -> bool:
        """Display login form and handle authentication."""
        st.markdown("# 🔐 Wine Email Generator - Login")
        st.markdown("Please log in to access the application.")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if self._verify_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
                    return False
        
        # Show demo credentials for development
        with st.expander("Demo Credentials (for testing)"):
            st.info("""
            **Demo accounts:**
            - Username: `admin`, Password: `password123`
            - Username: `demo`, Password: `demo123`
            
            **For production:** Configure credentials in Streamlit Cloud secrets.
            """)
        
        return False
    
    def logout(self):
        """Handle user logout."""
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return st.session_state.get('authenticated', False)
    
    def get_username(self) -> Optional[str]:
        """Get current authenticated username."""
        return st.session_state.get('username')
    
    def require_auth(self):
        """Decorator-like function to require authentication for a page."""
        if not self.is_authenticated():
            self.login_form()
            st.stop()
    
    def add_logout_button(self):
        """Add logout button to sidebar."""
        if self.is_authenticated():
            with st.sidebar:
                st.markdown(f"👤 Logged in as: **{self.get_username()}**")
                if st.button("🚪 Logout", key="logout_btn"):
                    self.logout()

# Global auth instance
auth = StreamlitAuth()