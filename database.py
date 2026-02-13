import sqlite3
from datetime import datetime
import os
import hashlib
import pandas as pd

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
        is_food BOOLEAN DEFAULT 0, -- 식료품 보관 장소 여부
        FOREIGN KEY (parent_id) REFERENCES locations (id)
    )
    ''')
    
    # Check if is_food column exists (Migration for existing DB)
    cursor.execute("PRAGMA table_info(locations)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'is_food' not in columns:
        cursor.execute('ALTER TABLE locations ADD COLUMN is_food BOOLEAN DEFAULT 0')
        print("Migrated: Added 'is_food' column to locations table.")
    
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
def add_location(name, category, parent_id=None, is_food=False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO locations (name, category, parent_id, is_food) VALUES (?, ?, ?, ?)', (name, category, parent_id, is_food))
    conn.commit()
    conn.close()

def get_locations():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_location(location_id, name, category, is_food):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE locations SET name=?, category=?, is_food=? WHERE id=?', (name, category, is_food, location_id))
    conn.commit()
    conn.close()

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

def get_location_by_id(loc_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations WHERE id = ?', (loc_id,))
    row = cursor.fetchone()
    conn.close()
    return row

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

# Data Management (Export/Import)
def export_all_data():
    conn = get_connection()
    # Get Locations
    loc_df = pd.read_sql_query("SELECT * FROM locations", conn)
    # Get Items
    item_df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()
    return loc_df, item_df

def import_locations(loc_df):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Clear existing locations
        cursor.execute("DELETE FROM locations")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='locations'")
        
        if not loc_df.empty:
            loc_data = loc_df.to_dict('records')
            cursor.executemany(
                'INSERT INTO locations (id, name, category, parent_id, is_food) VALUES (:id, :name, :category, :parent_id, :is_food)',
                loc_data
            )
            
        conn.commit()
        return True, "보관장소 데이터 가져오기 성공! (기존 데이터는 삭제되었습니다)"
    except Exception as e:
        conn.rollback()
        return False, f"보관장소 데이터 가져오기 실패: {str(e)}"
    finally:
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.close()

def import_items(item_df):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Clear existing items
        cursor.execute("DELETE FROM items")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='items'")
        
        if not item_df.empty:
            item_data = item_df.to_dict('records')
            cursor.executemany(
                'INSERT INTO items (id, name, purchase_date, expiry_date, quantity, notes, location_id) VALUES (:id, :name, :purchase_date, :expiry_date, :quantity, :notes, :location_id)',
                item_data
            )
            
        conn.commit()
        return True, "물품 데이터 가져오기 성공! (기존 데이터는 삭제되었습니다)"
    except Exception as e:
        conn.rollback()
        return False, f"물품 데이터 가져오기 실패: {str(e)}"
    finally:
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.close()
