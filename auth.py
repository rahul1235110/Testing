import streamlit as st
import hashlib
import hmac
import base64
import os
from database_pg import Database

class Auth:
    def __init__(self):
        """Initialize the authentication system."""
        self.db = Database()  # Will automatically use PostgreSQL if available
    
    def _hash_password(self, password, salt=None):
        """Hash a password for storing."""
        if salt is None:
            salt = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        )
        
        pw_hash = base64.b64encode(pw_hash).decode('utf-8')
        return f"{salt}${pw_hash}"
    
    def _verify_password(self, stored_password, provided_password):
        """Verify a stored password against one provided by user."""
        salt, stored_pw_hash = stored_password.split('$', 1)
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        pw_hash = base64.b64encode(pw_hash).decode('utf-8')
        return hmac.compare_digest(stored_pw_hash, pw_hash)
    
    def register_user(self, username, email, password):
        """Register a new user."""
        hashed_password = self._hash_password(password)
        return self.db.add_user(username, email, hashed_password)
    
    def login_user(self, username, password):
        """Validate user login."""
        user = self.db.get_user_by_username(username)
        
        if user and self._verify_password(user['password'], password):
            return user
        return None
    
    def display_login_form(self):
        """Display the login form."""
        if 'login_form_submitted' not in st.session_state:
            st.session_state.login_form_submitted = False
            
        if 'login_error' not in st.session_state:
            st.session_state.login_error = ""
        
        with st.form("login_form"):
            st.title("🔐 Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("Login")
            with col2:
                st.form_submit_button("I'm a new user", on_click=lambda: self._toggle_auth_form())
                
            if submitted:
                st.session_state.login_form_submitted = True
                user = self.login_user(username, password)
                
                if user:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.session_state.login_error = ""
                    st.rerun()
                else:
                    st.session_state.login_error = "Invalid username or password."
        
        if st.session_state.login_error:
            st.error(st.session_state.login_error)
    
    def display_register_form(self):
        """Display the registration form."""
        if 'register_form_submitted' not in st.session_state:
            st.session_state.register_form_submitted = False
        
        if 'register_error' not in st.session_state:
            st.session_state.register_error = ""
        
        with st.form("register_form"):
            st.title("🔐 Register")
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("Register")
            with col2:
                st.form_submit_button("I already have an account", on_click=lambda: self._toggle_auth_form())
            
            if submitted:
                st.session_state.register_form_submitted = True
                
                if not username or not email or not password:
                    st.session_state.register_error = "All fields are required."
                elif password != confirm_password:
                    st.session_state.register_error = "Passwords do not match."
                elif not self._is_valid_email(email):
                    st.session_state.register_error = "Please enter a valid email address."
                else:
                    success = self.register_user(username, email, password)
                    if success:
                        st.session_state.user = self.db.get_user_by_username(username)
                        st.session_state.authenticated = True
                        st.session_state.register_error = ""
                        st.rerun()
                    else:
                        st.session_state.register_error = "Username or email already exists."
        
        if st.session_state.register_error:
            st.error(st.session_state.register_error)
    
    def display_auth_page(self):
        """Display the authentication page based on current state."""
        if 'auth_form' not in st.session_state:
            st.session_state.auth_form = "login"
        
        if st.session_state.auth_form == "login":
            self.display_login_form()
        else:
            self.display_register_form()
    
    def _toggle_auth_form(self):
        """Toggle between login and registration forms."""
        if st.session_state.auth_form == "login":
            st.session_state.auth_form = "register"
        else:
            st.session_state.auth_form = "login"
    
    def _is_valid_email(self, email):
        """Basic email validation."""
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
    
    def logout_user(self):
        """Log out the current user."""
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()


