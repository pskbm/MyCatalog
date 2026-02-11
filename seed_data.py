import database as db
from datetime import datetime, timedelta

def seed_data():
    db.init_db()
    
    # Check if items exist
    if len(db.get_items()) > 0:
        print("Data already exists. Skipping seeding.")
        return

    # Get sample locations
    locs = db.get_locations()
    loc_map = {loc[2]: loc[0] for loc in locs} # category: id
    
    today = datetime.now()
    
    # 1. Expired item
    db.add_item("우유", (today - timedelta(days=10)).date().isoformat(), (today - timedelta(days=2)).date().isoformat(), 1, "유기농 우유", loc_map.get("냉장실"))
    
    # 2. Imminent item (D-1)
    db.add_item("계란", (today - timedelta(days=5)).date().isoformat(), (today + timedelta(days=1)).date().isoformat(), 10, "특란", loc_map.get("냉장실"))
    
    # 3. Healthy item
    db.add_item("쌀", (today - timedelta(days=30)).date().isoformat(), (today + timedelta(days=300)).date().isoformat(), 1, "햅쌀 10kg", loc_map.get("팬트리"))
    
    # 4. Imminent item (D-3)
    db.add_item("냉동 피자", (today - timedelta(days=20)).date().isoformat(), (today + timedelta(days=3)).date().isoformat(), 2, "콤비네이션", loc_map.get("냉동실"))

    print("Sample data seeded.")

if __name__ == "__main__":
    seed_data()
