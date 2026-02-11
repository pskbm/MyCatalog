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
    
    auth_tab1, auth_tab2 = st.tabs(["로그인", "회원가입"])
    
    with auth_tab1:
        with st.form("login_form"):
            st.subheader("로그인")
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
    
    with auth_tab2:
        with st.form("register_form"):
            st.subheader("새 계정 만들기")
            reg_un = st.text_input("새 아이디")
            reg_pw = st.text_input("새 비밀번호", type="password")
            reg_pw_confirm = st.text_input("비밀번호 확인", type="password")
            if st.form_submit_button("회원가입"):
                if reg_un and reg_pw:
                    if reg_pw == reg_pw_confirm:
                        if db.register_user(reg_un, reg_pw):
                            st.success("회원가입이 완료되었습니다! 로그인을 해주세요.")
                        else:
                            st.error("이미 존재하는 아이디입니다.")
                    else:
                        st.error("비밀번호가 일치하지 않습니다.")
                else:
                    st.error("아이디와 비밀번호를 모두 입력해 주세요.")
    st.stop()

# --- Main Application Area (Authenticated) ---
# Sidebar Navigation
st.sidebar.title(f"👤 {st.session_state.username}님")
if st.sidebar.button("로그아웃"):
    logout_user()

st.sidebar.divider()
menu = st.sidebar.selectbox("메뉴 선택", ["대시보드", "물품 관리", "보관 장소 설정", "알림 센터", "계정 설정"])

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
        
        expired = df[df['expiry_date'] < today]
        imminent = df[(df['expiry_date'] >= today) & (df['expiry_date'] <= today + pd.Timedelta(days=7))]
        
        # Top Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card("전체 물품", len(df), "#764ba2", "📦")
        with col2:
            render_metric_card("유통기한 경과", len(expired), "#e74c3c", "⚠️")
        with col3:
            render_metric_card("7일 이내 만료", len(imminent), "#f39c12", "⏰")
            
        st.divider()
        
        # Category breakdown
        st.subheader("📍 보관 장소별 현황")
        categories = df['category'].unique()
        cols = st.columns(len(categories))
        for i, cat in enumerate(categories):
            cat_items = df[df['category'] == cat]
            cat_expired = len(cat_items[cat_items['expiry_date'] < today])
            cat_total = len(cat_items)
            with cols[i]:
                st.markdown(f"""
                <div class="stCard">
                    <h3>{cat}</h3>
                    <p style="font-size: 1.5rem; font-weight:700;">{cat_total}개</p>
                    <p style="color:red; font-size: 0.9rem;">만료: {cat_expired}개</p>
                </div>
                """, unsafe_allow_html=True)
                
        # List of imminent/expired items
        if not imminent.empty or not expired.empty:
            st.subheader("🔔 주의가 필요한 물품")
            alert_df = pd.concat([expired, imminent])
            st.dataframe(alert_df[["name", "expiry_date", "location_name", "category"]].sort_values("expiry_date"), use_container_width=True)
    else:
        st.info("등록된 물품이 없습니다. '물품 관리' 메뉴에서 물품을 등록해 보세요!")

elif menu == "물품 관리":
    st.title("📋 물품 관리")
    
    # Registration tab, View/Edit tab
    tab1, tab2 = st.tabs(["물품 등록", "전체 목록"])
    
    with tab1:
        st.subheader("새 물품 등록")
        with st.form("add_item_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("📦 품목명")
                quantity = st.number_input("수량", min_value=1.0, step=0.5, value=1.0)
                purchase_date = st.date_input("구매 일자", value=datetime.today())
            with col2:
                # Default expiry date: 10 years later
                default_expiry = datetime.today() + pd.DateOffset(years=10)
                expiry_date = st.date_input("유통기한", value=default_expiry)
                locations = db.get_locations()
                if locations:
                    loc_options = {f"[{loc[2]}] {loc[1]}": loc[0] for loc in locations}
                    location_label = st.selectbox("보관 장소", options=list(loc_options.keys()))
                    location_id = loc_options[location_label]
                else:
                    st.warning("먼저 '보관 장소 설정'에서 장소를 등록해 주세요.")
                    location_id = None
                notes = st.text_area("참고사항")
                
            submit = st.form_submit_button("등록하기")
            if submit:
                if name and location_id:
                    db.add_item(name, purchase_date.isoformat(), expiry_date.isoformat(), quantity, notes, location_id)
                    st.success(f"'{name}' 등록 완료!")
                    st.balloons()
                elif not name:
                    st.error("품목명을 입력해 주세요.")
                else:
                    st.error("보관 장소를 선택해 주세요.")

    with tab2:
        df = get_all_items_with_info()
        if not df.empty:
            # 1. Category Filter at the top
            st.subheader("🕵️ 카테고리별 필터링")
            categories = sorted(df['category'].unique())
            # Default to "기타" if it exists, otherwise the first one
            default_cat_idx = categories.index("기타") if "기타" in categories else 0
            selected_cat = st.selectbox("조회할 대분류 선택", options=categories, index=default_cat_idx)
            
            # 2. Show Filtered List
            filtered_df = df[df['category'] == selected_cat]
            st.markdown(f"**'{selected_cat}'** 카테고리에 총 {len(filtered_df)}개의 물품이 있습니다.")
            st.dataframe(filtered_df.drop(columns=['id', 'location_id']), use_container_width=True)
            
            st.markdown("---")
            
            # 3. Item Selection for Edit/Delete from the filtered list
            if not filtered_df.empty:
                st.subheader("📝 물품 수정 및 삭제")
                selected_item_id = st.selectbox(
                    "수정 또는 삭제할 물품을 선택하세요", 
                    options=filtered_df['id'].tolist(), 
                    format_func=lambda x: f"{filtered_df[filtered_df['id']==x]['name'].iloc[0]} ({filtered_df[filtered_df['id']==x]['location_name'].iloc[0]})"
                )
                item_data = filtered_df[filtered_df['id'] == selected_item_id].iloc[0]
                
                with st.form(f"edit_form_{selected_item_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        u_name = st.text_input("품목명", value=item_data['name'])
                        u_qty = st.number_input("수량", value=float(item_data['quantity']), step=0.5)
                    with col2:
                        u_expiry = st.date_input("유통기한", value=pd.to_datetime(item_data['expiry_date']).date())
                        # Get locations for re-assignment
                        locs_edit = db.get_locations()
                        loc_edit_options = {f"[{l[2]}] {l[1]}": l[0] for l in locs_edit}
                        # Current location label
                        current_loc_label = next((k for k, v in loc_edit_options.items() if v == item_data['location_id']), None)
                        
                        u_loc_label = st.selectbox(
                            "보관 장소 변경", 
                            options=list(loc_edit_options.keys()), 
                            index=list(loc_edit_options.keys()).index(current_loc_label) if current_loc_label and current_loc_label in loc_edit_options else 0
                        )
                        u_loc_id = loc_edit_options[u_loc_label] if loc_edit_options else None
                    
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
    
    col1, col2 = st.columns(2)
    with col1:
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
            
            if st.form_submit_button("장소 등록"):
                if new_loc_name:
                    # Logic: If select name-same, use name. If direct, use custom. Else use selected.
                    final_cat = new_loc_name
                    if selected_cat == "직접 입력":
                        final_cat = custom_cat if custom_cat else new_loc_name
                    elif selected_cat != "(장소 이름과 동일)":
                        final_cat = selected_cat
                    
                    db.add_location(new_loc_name, final_cat, None)
                    st.success(f"'{new_loc_name}' ({final_cat}) 등록 완료!")
                    st.rerun()
                else:
                    st.error("장소 이름을 입력해 주세요.")
    
    with col2:
        st.subheader("등록된 장소 관리")
        locs = db.get_locations()
        if locs:
            loc_df = pd.DataFrame(locs, columns=['id', 'name', 'category', 'parent_id'])
            st.table(loc_df[['category', 'name']])
            
            st.divider()
            st.write("🗑️ 장소 삭제")
            # Filter out top-level category placeholders if they are fixed, 
            # but here they are just normal locations.
            del_loc_id = st.selectbox("삭제할 장소 선택", options=loc_df['id'].tolist(), 
                                      format_func=lambda x: f"[{loc_df[loc_df['id']==x]['category'].iloc[0]}] {loc_df[loc_df['id']==x]['name'].iloc[0]}")
            
            if st.button("선택한 장소 삭제"):
                db.delete_location_safely(del_loc_id)
                st.warning(f"장소가 삭제되었습니다. 해당 장소의 물품은 '없음(대분류 최상위)'으로 변경되었습니다.")
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

elif menu == "계정 설정":
    st.title("⚙️ 계정 설정")
    st.markdown(f"**현재 로그인 계정:** {st.session_state.username}")
    
    st.divider()
    st.subheader("⚠️ 계정 탈퇴")
    st.warning("계정을 삭제하더라도 등록하신 보관장소와 물품 정보는 공유 데이터로 남게 됩니다.")
    
    confirm_un = st.text_input("탈퇴를 진행하시려면 아이디를 입력하세요")
    if st.button("계정 삭제"):
        if confirm_un == st.session_state.username:
            db.delete_user(st.session_state.user_id)
            st.success("계정이 삭제되었습니다. 이용해 주셔서 감사합니다.")
            logout_user()
        else:
            st.error("입력하신 아이디가 일치하지 않습니다.")
