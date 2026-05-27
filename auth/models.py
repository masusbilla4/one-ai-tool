"""
Authentication models and Supabase auth helpers.
"""
import os
import json
import hashlib
from datetime import datetime
from supabase import create_client, Client

from config import Config


def get_supabase_client() -> Client:
    """Create and return Supabase client."""
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_user_by_username(username: str) -> dict:
    """Get user by username from Supabase."""
    try:
        client = get_supabase_client()
        response = client.table('app_users').select('*').eq('username', username).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def get_user_by_id(user_id: int) -> dict:
    """Get user by ID from Supabase."""
    try:
        client = get_supabase_client()
        response = client.table('app_users').select('*').eq('id', user_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def create_user(username: str, password: str, email: str = '') -> tuple:
    """
    Create a new user.
    Returns: (success: bool, message: str)
    """
    try:
        client = get_supabase_client()
        
        # Check if username exists
        existing = get_user_by_username(username)
        if existing:
            return False, "Username already exists"
        
        # Insert new user
        user_data = {
            'username': username,
            'password_hash': hash_password(password),
            'email': email,
            'created_at': datetime.now().isoformat(),
            'is_admin': False
        }
        
        response = client.table('app_users').insert(user_data).execute()
        if response.data:
            return True, "User created successfully"
        return False, "Failed to create user"
    except Exception as e:
        return False, f"Error: {str(e)}"


def authenticate_user(username: str, password: str) -> tuple:
    """
    Authenticate user login.
    Returns: (success: bool, user: dict or None, message: str)
    """
    try:
        user = get_user_by_username(username)
        if not user:
            return False, None, "Invalid username or password"
        
        if user.get('password_hash') == hash_password(password):
            return True, user, "Login successful"
        return False, None, "Invalid username or password"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def get_all_users() -> list:
    """Get all users from Supabase (admin only)."""
    try:
        client = get_supabase_client()
        response = client.table('app_users').select('id, username, email, created_at, is_admin').order('created_at', desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting users: {e}")
        return []


def delete_user(user_id: int) -> tuple:
    """
    Delete a user (admin only).
    Returns: (success: bool, message: str)
    """
    try:
        client = get_supabase_client()
        response = client.table('app_users').delete().eq('id', user_id).execute()
        if response.data is not None or True:  # Supabase returns empty on success
            return True, "User deleted"
        return False, "Failed to delete user"
    except Exception as e:
        return False, f"Error: {str(e)}"


def update_user_password(user_id: int, new_password: str) -> tuple:
    """
    Update user password (admin only).
    Returns: (success: bool, message: str)
    """
    try:
        client = get_supabase_client()
        response = client.table('app_users').update({
            'password_hash': hash_password(new_password),
            'password_updated_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        if response.data:
            return True, "Password updated"
        return False, "Failed to update password"
    except Exception as e:
        return False, f"Error: {str(e)}"


def set_user_admin(user_id: int, is_admin: bool) -> tuple:
    """
    Set user admin status (admin only).
    Returns: (success: bool, message: str)
    """
    try:
        client = get_supabase_client()
        response = client.table('app_users').update({'is_admin': is_admin}).eq('id', user_id).execute()
        if response.data:
            return True, "User updated"
        return False, "Failed to update user"
    except Exception as e:
        return False, f"Error: {str(e)}"


def init_users_table():
    """
    Initialize the app_users table in Supabase.
    Run this once to create the table structure.
    Note: This requires admin privileges in Supabase.
    """
    # This would typically be done via Supabase dashboard or SQL
    # The table structure should be:
    """
    CREATE TABLE app_users (
        id BIGSERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        is_admin BOOLEAN DEFAULT FALSE,
        password_updated_at TIMESTAMP
    );
    """
    pass
