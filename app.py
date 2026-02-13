import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
from styles import apply_custom_styles, render_metric_card

st.set_page_config(
    page_title="MyCatalog - 스마트 물품 관리",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
db.init_db()

# Apply Custom CSS
apply_custom_styles()

# Authentication State Management
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

def login_user(id, username):
    st.session_state.logged_in = True
    st.session_state.user_id = id
    st.session_state.username = username

def logout_user():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()

# 🔑 Auth Screen
if not st.session_state.logged_in:
    st.markdown("""
    <div style="text-align: center; padding: 50px 0;">
        <h1 style="font-size: 3rem; margin-bottom: 10px;">📦 MyCatalog</h1>
        <p style="color: #666; font-size: 1.2rem;">스마트한 물품 관리를 위한 첫 걸음</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Remove tabs, only Login
    with st.container():
        st.subheader("로그인")
        with st.form("login_form"):
            login_un = st.text_input("아이디")
            login_pw = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                user = db.authenticate_user(login_un, login_pw)
                if user:
                    login_user(user[0], user[1])
                    st.success(f"{user[1]}님, 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
    st.stop()

# --- Main Application Area (Authenticated) ---
# Sidebar Navigation
st.sidebar.title(f"👤 {st.session_state.username}님")
if st.sidebar.button("로그아웃"):
    logout_user()

st.sidebar.divider()
menu_options = ["대시보드", "물품 관리", "보관 장소 설정", "알림 센터"]
if st.session_state.username == "skpark":
    menu_options.append("회원 관리")

menu = st.sidebar.selectbox("메뉴 선택", menu_options)

# Helper: Get all items with location info
def get_all_items_with_info():
    items = db.get_items()
    locations = {loc[0]: (loc[1], loc[2]) for loc in db.get_locations()} # id: (name, cat)
    data = []
    for itm in items:
        # User requirement: If location is None/deleted, show "없음(대분류 최상위)"
        loc_id = itm[6]
        if loc_id and loc_id in locations:
            loc_info = locations[loc_id]
        else:
            loc_info = ("없음(대분류 최상위)", "기타")
            
        data.append({
            "id": itm[0],
            "name": itm[1],
            "purchase_date": itm[2],
            "expiry_date": itm[3],
            "quantity": itm[4],
            "notes": itm[5],
            "location_id": itm[6], # Added this line
            "location_name": loc_info[0],
            "category": loc_info[1]
        })
    return pd.DataFrame(data)

if menu == "대시보드":
    st.title("🏡 My Home Dashboard")
    st.write(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")
    
    df = get_all_items_with_info()
    
    if not df.empty:
        today = datetime.now().date()
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
        
    st.title("📊 대시보드")
    
    # ... (Rest of Dashboard code remains mostly same, just ensuring data consistency)
    items = get_all_items_with_info() 
    # Use the local function
    
    total_items = len(items)
    
    # Calculate expiry statuses
    today = datetime.now().date()
    expired_count = 0
    imminent_count = 0
    
    if not items.empty:
        for index, row in items.iterrows():
            exp_date = datetime.strptime(row['expiry_date'], '%Y-%m-%d').date()
            diff = (exp_date - today).days
            if diff < 0:
                expired_count += 1
            elif diff <= 7:
                imminent_count += 1
    
    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("전체 물품", total_items, "#764ba2", "📦")
    with col2:
        render_metric_card("유통기한 경과", expired_count, "#e74c3c", "⚠️")
    with col3:
        render_metric_card("7일 이내 만료", imminent_count, "#f39c12", "⏰")
    
    st.divider()
    
    if not items.empty:
        st.subheader("📦 카테고리별 현황")
        cat_counts = items['category'].value_counts()
        st.bar_chart(cat_counts)

        # List of imminent/expired items
        st.subheader("🔔 주의가 필요한 물품")
        items['expiry_date_dt'] = pd.to_datetime(items['expiry_date']).dt.date
        expired_df = items[items['expiry_date_dt'] < today]
        imminent_df = items[(items['expiry_date_dt'] >= today) & (items['expiry_date_dt'] <= today + pd.Timedelta(days=7))]
        
        if not imminent_df.empty or not expired_df.empty:
            alert_df = pd.concat([expired_df, imminent_df])
            st.dataframe(alert_df[["name", "expiry_date", "location_name", "category"]].sort_values("expiry_date"), use_container_width=True)
        else:
            st.info("유통기한이 임박하거나 만료된 물품이 없습니다.")
    else:
        st.info("등록된 물품이 없습니다. '물품 관리' 메뉴에서 물품을 등록해 보세요!")

elif menu == "물품 관리":
    st.title("📦 물품 등록 및 관리")
    
    tab1, tab2 = st.tabs(["물품 등록", "전체 목록 및 수정"])
    
    with tab1:
        st.subheader("새 물품 등록")
        
        # Location Selection Moved OUTSIDE the form to trigger rerun
        locations = db.get_locations()
        if locations:
            # loc tuple: (id, name, category, parent_id, is_food)
            loc_options = {f"[{loc[2]}] {loc[1]} {'🍎' if len(loc)>4 and loc[4] else ''}": loc for loc in locations}
            selected_loc_label = st.selectbox("보관 장소 선택", list(loc_options.keys()))
            selected_loc = loc_options[selected_loc_label]
            location_id = selected_loc[0]
            is_food_loc = selected_loc[4] if len(selected_loc) > 4 else 0
        else:
            st.warning("등록된 보관 장소가 없습니다. '보관 장소 설정'에서 장소를 먼저 등록해 주세요.")
            location_id = None
            is_food_loc = 0

        # Dynamic Default Expiry Calculation
        if is_food_loc:
            default_expiry = datetime.today() + pd.DateOffset(days=15)
            help_text = "식료품 보관 장소이므로 기본값이 15일 후로 설정되었습니다."
        else:
            default_expiry = datetime.today() + pd.DateOffset(years=10)
            help_text = "일반 보관 장소이므로 기본값이 10년 후로 설정되었습니다."

        with st.form("add_item_form"):
            name = st.text_input("📦 품목명")
            
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input("수량", min_value=1.0, step=0.5, value=1.0)
                purchase_date = st.date_input("구매 일자", value=datetime.today())
            with col2:
                # Use key to force re-render when location changes
                # But we also need to allow user to change it manually without it resetting on every slight interaction if we used a random key.
                # Using location_id in key means it only resets when location changes. Perfect.
                expiry_date = st.date_input("유통기한", value=default_expiry, help=help_text, key=f"expiry_input_{location_id}")
            
            notes = st.text_area("참고사항")
            
            if st.form_submit_button("등록"):
                if name:
                    if location_id:
                        db.add_item(name, purchase_date.isoformat(), expiry_date.isoformat(), quantity, notes, location_id)
                        st.success(f"'{name}' 등록 완료!")
                        st.balloons()
                    else:
                        st.error("보관 장소를 선택해 주세요.")
                else:
                    st.error("품목명을 입력해 주세요.")

    with tab2:
        df = get_all_items_with_info()
        if not df.empty:
            # 1. Category Filter at the top
            st.subheader("🕵️ 카테고리별 필터링")
            categories = sorted(df['category'].unique())
            default_cat_idx = categories.index("기타") if "기타" in categories else 0
            selected_cat = st.selectbox("조회할 대분류 선택", options=categories, index=default_cat_idx)
            
            # 2. Show Filtered List
            filtered_df = df[df['category'] == selected_cat]
            st.markdown(f"**'{selected_cat}'** 카테고리에 총 {len(filtered_df)}개의 물품이 있습니다.")
            st.dataframe(filtered_df.drop(columns=['id', 'location_id']), use_container_width=True)
            
            st.markdown("---")
            
            # 3. Item Selection for Edit/Delete
            if not filtered_df.empty:
                st.subheader("📝 물품 수정 및 삭제")
                selected_item_id = st.selectbox(
                    "수정 또는 삭제할 물품을 선택하세요", 
                    options=filtered_df['id'].tolist(), 
                    format_func=lambda x: f"{filtered_df[filtered_df['id']==x]['name'].iloc[0]} ({filtered_df[filtered_df['id']==x]['location_name'].iloc[0]})"
                )
                item_data = filtered_df[filtered_df['id'] == selected_item_id].iloc[0]
                
                with st.form(f"edit_form_{selected_item_id}"):
                    u_name = st.text_input("품목명", value=item_data['name'])
                    
                    # Update Location options in Edit
                    locs_edit = db.get_locations()
                    loc_edit_options = {f"[{l[2]}] {l[1]}": l[0] for l in locs_edit}
                    
                    current_loc_label = next((k for k, v in loc_edit_options.items() if v == item_data['location_id']), None)
                    u_loc_label = st.selectbox(
                        "보관 장소 변경", 
                        options=list(loc_edit_options.keys()), 
                        index=list(loc_edit_options.keys()).index(current_loc_label) if current_loc_label and current_loc_label in loc_edit_options else 0
                    )
                    u_loc_id = loc_edit_options[u_loc_label] if loc_edit_options else None
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        u_qty = st.number_input("수량", value=float(item_data['quantity']), step=0.5)
                    with col2:
                        u_expiry = st.date_input("유통기한", value=pd.to_datetime(item_data['expiry_date']).date())
                    
                    u_notes = st.text_area("참고사항", value=item_data['notes'])
                    
                    c1, c2, _ = st.columns([1, 1, 2])
                    with c1:
                        if st.form_submit_button("💾 수정 사항 저장"):
                            db.update_item(selected_item_id, u_name, item_data['purchase_date'], u_expiry.isoformat(), u_qty, u_notes, u_loc_id)
                            st.success("수정되었습니다!")
                            st.rerun()
                    with c2:
                        if st.form_submit_button("🗑️ 물품 삭제"):
                            db.delete_item(selected_item_id)
                            st.warning("삭제되었습니다.")
                            st.rerun()
            else:
                st.info(f"'{selected_cat}' 카테고리에 등록된 물품이 없습니다.")
        else:
            st.write("목록이 비어 있습니다.")

elif menu == "보관 장소 설정":
    st.title("⚙️ 보관 장소 관리")
    
    tab_loc1, tab_loc2 = st.tabs(["장소 등록", "장소 수정/삭제"])
    
    with tab_loc1:
        st.subheader("새 장소 등록")
        with st.form("add_loc_form"):
            new_loc_name = st.text_input("장소 이름 (예: 냉장실, 거실 서랍 등)")
            
            # Get unique existing categories
            locs_raw = db.get_locations()
            existing_categories = sorted(list(set([loc[2] for loc in locs_raw])))
            
            cat_options = ["(장소 이름과 동일)"] + existing_categories + ["직접 입력"]
            selected_cat = st.selectbox("대분류 선택", cat_options)
            
            custom_cat = ""
            if selected_cat == "직접 입력":
                custom_cat = st.text_input("새 대분류명 입력")
            
            is_food_check = st.checkbox("식료품 보관 장소인가요?", help="체크 시 이 장소에 물품 등록 시 유통기한 기본값이 15일로 설정됩니다.")
            
            if st.form_submit_button("장소 등록"):
                if new_loc_name:
                    final_cat = new_loc_name
                    if selected_cat == "직접 입력":
                        final_cat = custom_cat if custom_cat else new_loc_name
                    elif selected_cat != "(장소 이름과 동일)":
                        final_cat = selected_cat
                    
                    db.add_location(new_loc_name, final_cat, None, is_food_check)
                    st.success(f"'{new_loc_name}' ({final_cat}) 등록 완료!")
                    st.rerun()
                else:
                    st.error("장소 이름을 입력해 주세요.")
    
    with tab_loc2:
        st.subheader("등록된 장소 관리")
        locs = db.get_locations()
        if locs:
            # Prepare DataFrame
            # loc: id, name, category, parent_id, is_food
            loc_data = []
            for l in locs:
                is_food_val = l[4] if len(l) > 4 else 0
                loc_data.append({
                    "id": l[0],
                    "name": l[1],
                    "category": l[2],
                    "is_food": "✅" if is_food_val else "-"
                })
            
            loc_df = pd.DataFrame(loc_data)
            st.dataframe(loc_df[['category', 'name', 'is_food']], use_container_width=True)
            
            st.divider()
            
            # Edit/Delete Section
            selected_loc_id = st.selectbox("관리할 장소 선택", options=loc_df['id'].tolist(), 
                                      format_func=lambda x: f"[{loc_df[loc_df['id']==x]['category'].iloc[0]}] {loc_df[loc_df['id']==x]['name'].iloc[0]}")
            
            loc_to_edit = db.get_location_by_id(selected_loc_id)
            # loc_to_edit: tuple (id, name, cat, parent, is_food)
            
            with st.form("edit_loc_form"):
                st.markdown(f"**'{loc_to_edit[1]}'** 수정 중")
                u_loc_name = st.text_input("장소 이름", value=loc_to_edit[1])
                u_loc_cat = st.text_input("대분류", value=loc_to_edit[2]) 
                u_is_food = st.checkbox("식료품 보관 장소", value=bool(loc_to_edit[4]) if len(loc_to_edit)>4 else False)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("수정 저장"):
                        db.update_location(selected_loc_id, u_loc_name, u_loc_cat, u_is_food)
                        st.success("장소 정보가 수정되었습니다.")
                        st.rerun()
                with c2:
                    if st.form_submit_button("🗑️ 장소 삭제"):
                        db.delete_location_safely(selected_loc_id)
                        st.warning("장소가 삭제되었습니다.")
                        st.rerun()
        else:
            st.info("등록된 장소가 없습니다.")

elif menu == "알림 센터":
    st.title("🔔 유통기한 알림")
    alerts = db.get_expiry_alerts()
    
    if alerts:
        today = datetime.now().date()
        for alt in alerts:
            expiry = datetime.strptime(alt[3], '%Y-%m-%d').date()
            diff = (expiry - today).days
            
            if diff < 0:
                severity = "error"
                label = f"만료됨 ({abs(diff)}일 경과)"
            elif diff == 0:
                severity = "warning"
                label = "오늘 만료!!"
            elif diff <= 3:
                severity = "warning"
                label = f"D-{diff} (임박)"
            else:
                severity = "info"
                label = f"D-{diff}"
            
            st.toast(f"{alt[1]}이(가) {label} 입니다!", icon="⚠️")
            
            with st.chat_message("user" if severity=="error" else "assistant"):
                st.write(f"**{alt[1]}** - {alt[3]} ({label})")
                st.write(f"위치: {alt[7]} > {alt[1]}") # cat > name
    else:
        st.success("유통기한이 임박한 물품이 없습니다. 편안한 하루 되세요! 😊")

elif menu == "회원 관리":
    st.title("👥 회원 관리 (관리자 전용)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("새 회원 등록")
        with st.form("admin_register_form"):
            reg_un = st.text_input("새 아이디")
            reg_pw = st.text_input("새 비밀번호", type="password")
            reg_pw_confirm = st.text_input("비밀번호 확인", type="password")
            
            if st.form_submit_button("회원 등록"):
                if reg_un and reg_pw:
                    if reg_pw == reg_pw_confirm:
                        if db.register_user(reg_un, reg_pw):
                            st.success(f"'{reg_un}' 계정이 생성되었습니다.")
                            st.rerun()
                        else:
                            st.error("이미 존재하는 아이디입니다.")
                    else:
                        st.error("비밀번호가 일치하지 않습니다.")
                else:
                    st.error("모든 필드를 입력해 주세요.")
                    
    with col2:
        st.subheader("회원 목록 및 삭제")
        users = db.get_all_users()
        if users:
            user_df = pd.DataFrame(users, columns=['ID', 'Username'])
            st.dataframe(user_df[['Username']], use_container_width=True)
            
            st.divider()
            st.write("🗑️ 회원 삭제")
            
            # Deletion UI
            del_user_id = st.selectbox("삭제할 회원 선택", options=user_df['ID'].tolist(), 
                                     format_func=lambda x: user_df[user_df['ID']==x]['Username'].iloc[0])
            
            if st.button("선택한 회원 삭제"):
                selected_username = user_df[user_df['ID']==del_user_id]['Username'].iloc[0]
                if selected_username == "skpark":
                    st.error("관리자 계정(skpark)은 삭제할 수 없습니다.")
                elif selected_username == st.session_state.username:
                    st.error("현재 로그인된 계정은 삭제할 수 없습니다.")
                else:
                    db.delete_user(del_user_id)
                    st.success(f"'{selected_username}' 계정이 삭제되었습니다.")
                    st.rerun()
        else:
            st.info("등록된 회원이 없습니다.")
