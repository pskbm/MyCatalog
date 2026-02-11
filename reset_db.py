import database as db
import sqlite3

def reset_database():
    conn = db.get_connection()
    cursor = conn.cursor()
    # Delete all items and locations
    cursor.execute('DELETE FROM items')
    cursor.execute('DELETE FROM locations')
    # Make sure initialized is true so it doesn't re-seed
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("initialized", "true")')
    conn.commit()
    conn.close()
    print("Database cleared. Ready for new input.")

if __name__ == "__main__":
    reset_database()
