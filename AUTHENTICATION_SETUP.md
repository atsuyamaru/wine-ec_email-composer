# Authentication Setup Guide

## Overview

This Wine Email Generator app now includes a secure login feature to prevent unauthorized access when deployed on Streamlit Cloud. The authentication system uses session-based login with username/password combinations.

## Features

- ✅ Session-based authentication
- ✅ Secure credential management via Streamlit secrets
- ✅ Automatic logout functionality
- ✅ Protected all app pages (Single Wine, PDF Import, Wine Library, 6 Bottles Package)
- ✅ User-friendly login interface
- ✅ Demo credentials for testing

## For Local Development

When running the app locally, it uses default demo credentials:

- **Username:** `admin`, **Password:** `password123`
- **Username:** `demo`, **Password:** `demo123`

These are automatically available when `st.secrets` is not configured.

## For Production (Streamlit Cloud)

### Step 1: Configure Secrets in Streamlit Cloud

1. Go to your Streamlit Cloud dashboard
2. Open your app settings
3. Navigate to the "Secrets" section
4. Add the following configuration:

```toml
[credentials]
admin = "your_strong_password_here"
user1 = "another_secure_password"
manager = "manager_password"
```

### Step 2: Generate Secure Passwords

For security, generate strong passwords using Python:

```python
import secrets
print(secrets.token_urlsafe(32))  # Generates a secure 32-character password
```

### Step 3: Deploy Your App

Once secrets are configured, deploy your app. Users will need to authenticate before accessing any functionality.

## Security Features

### What's Protected
- ✅ All main pages require authentication
- ✅ Session state is used to maintain login status
- ✅ Logout functionality clears session
- ✅ Direct page access blocked without login

### Login Flow
1. User visits any page
2. If not authenticated, login form is displayed
3. Upon successful login, user is redirected to requested page
4. Session persists across page navigation
5. Logout button available in sidebar

### Password Security
- Passwords are compared directly (for simplicity)
- For enhanced security, consider implementing password hashing
- Credentials stored securely in Streamlit Cloud secrets

## File Changes Made

### New Files
- `auth.py` - Authentication module with login/logout functionality
- `.streamlit/secrets.toml` - Template for secrets configuration
- `AUTHENTICATION_SETUP.md` - This setup guide

### Modified Files
- `single_wine.py` - Added authentication requirement
- `pages/pdf_import.py` - Added authentication requirement  
- `pages/wine_library.py` - Added authentication requirement
- `pages/packages_6bottles.py` - Added authentication requirement

## Usage

### For Administrators
1. Set up strong credentials in Streamlit Cloud secrets
2. Share login credentials securely with authorized users
3. Monitor access as needed

### For Users
1. Navigate to the app URL
2. Enter provided username and password
3. Access all app features as normal
4. Use logout button when finished

## Troubleshooting

### Common Issues

**Q: Login form not appearing**
- Check that `auth.py` is in the root directory
- Ensure all pages import and call `auth.require_auth()`

**Q: "Invalid credentials" even with correct password**
- Verify secrets configuration in Streamlit Cloud
- Check for typos in username/password
- Ensure credentials section is properly formatted

**Q: Logged out unexpectedly**
- This happens when session state is cleared
- Simply log in again - this is normal behavior

**Q: Can't access secrets locally**
- Local development uses default demo credentials
- No secrets.toml file needed for local testing

## Advanced Customization

### Adding More Users
Add new username/password pairs to the credentials section:

```toml
[credentials]
admin = "admin_password"
user1 = "user1_password"
user2 = "user2_password"
manager = "manager_password"
```

### Customizing Login UI
Edit the `login_form()` method in `auth.py` to modify:
- Page title and styling
- Form layout
- Error messages
- Demo credentials display

### Session Timeout
Currently, sessions persist until:
- User clicks logout
- Browser session ends
- Streamlit app restarts

To add session timeout, modify the authentication logic in `auth.py`.

## Security Best Practices

1. **Use Strong Passwords**: Generate random, long passwords
2. **Regular Updates**: Rotate passwords periodically
3. **Limited Sharing**: Only share credentials with authorized users
4. **Monitor Access**: Keep track of who has access
5. **Secure Communication**: Share credentials through secure channels

## Contact & Support

If you encounter issues with authentication setup:
1. Check this guide first
2. Verify Streamlit Cloud secrets configuration
3. Test with demo credentials locally
4. Review error messages in the app

The authentication system is designed to be simple yet secure for protecting your wine email generator from unauthorized access.