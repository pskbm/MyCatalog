import sqlite3
from datetime import datetime
import os
import hashlib

DB_PATH = 'mycatalog.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
    
    # Locations table (Hierarchical)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- 대분류 (냉장실, 냉동실, 팬트리 등)
        parent_id INTEGER,
        FOREIGN KEY (parent_id) REFERENCES locations (id)
    )
    ''')
    
    # Items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        purchase_date DATE,
        expiry_date DATE,
        quantity REAL DEFAULT 1,
        notes TEXT,
        location_id INTEGER,
        FOREIGN KEY (location_id) REFERENCES locations (id)
    )
    ''')
    
    # Settings table to track initialization
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    
    # Check initialization flag
    cursor.execute('SELECT value FROM settings WHERE key = "initialized"')
    if not cursor.fetchone():
        # No default categories anymore as per user request
        cursor.execute('INSERT INTO settings (key, value) VALUES ("initialized", "true")')
    
    # Create default admin user 'skpark' if no users exist
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        # Default password for skpark is '1234'
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                       ("skpark", hash_password("1234")))
        print("Default admin user 'skpark' created (password: 1234)")

    conn.commit()
    conn.close()

# Location CRUD
def add_location(name, category, parent_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO locations (name, category, parent_id) VALUES (?, ?, ?)', (name, category, parent_id))
    conn.commit()
    conn.close()

def get_locations():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations')
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_location_safely(location_id):
    conn = get_connection()
    cursor = conn.cursor()
    # Reassign items to NULL (meaning Unassigned/Top-level)
    cursor.execute('UPDATE items SET location_id = NULL WHERE location_id = ?', (location_id,))
    # Delete the location
    cursor.execute('DELETE FROM locations WHERE id = ?', (location_id,))
    conn.commit()
    conn.close()

# Item CRUD
def add_item(name, purchase_date, expiry_date, quantity, notes, location_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO items (name, purchase_date, expiry_date, quantity, notes, location_id)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, purchase_date, expiry_date, quantity, notes, location_id))
    conn.commit()
    conn.close()

def get_items(location_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if location_id:
        cursor.execute('SELECT * FROM items WHERE location_id = ?', (location_id,))
    else:
        cursor.execute('SELECT * FROM items')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_item(item_id, name, purchase_date, expiry_date, quantity, notes, location_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE items SET name=?, purchase_date=?, expiry_date=?, quantity=?, notes=?, location_id=?
    WHERE id=?
    ''', (name, purchase_date, expiry_date, quantity, notes, location_id, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

def get_expiry_alerts():
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    # Expired or expiring within 30 days
    cursor.execute('''
    SELECT items.*, locations.category 
    FROM items 
    JOIN locations ON items.location_id = locations.id
    WHERE expiry_date <= date(?, '+30 days')
    ORDER BY expiry_date ASC
    ''', (today,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# User Auth Functions
def register_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                       (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE username = ? AND password_hash = ?', 
                   (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user # returns (id, username) or None

def delete_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
