import streamlit as st
import pandas as pd
from datetime import datetime
import os
import database as db
import ocr_helper
from styles import apply_custom_styles, render_metric_card

st.set_page_config(
    page_title="MyCatalog - 스마트 물품 관리",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
db.init_db()
os.makedirs("uploads", exist_ok=True)

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
menu_options = ["대시보드", "물품 관리", "카테고리 설정", "영수증 관리", "알림 센터"]
if st.session_state.username == "skpark":
    menu_options.append("회원 관리")
    menu_options.append("데이터 관리")

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
            selected_loc_label = st.selectbox("카테고리 선택", list(loc_options.keys()))
            selected_loc = loc_options[selected_loc_label]
            location_id = selected_loc[0]
            is_food_loc = selected_loc[4] if len(selected_loc) > 4 else 0
        else:
            st.warning("등록된 카테고리가 없습니다. '카테고리 설정'에서 카테고리를 먼저 등록해 주세요.")
            location_id = None
            is_food_loc = 0

        # Dynamic Default Expiry Calculation
        if is_food_loc:
            default_expiry = datetime.today() + pd.DateOffset(days=15)
            help_text = "식료품 카테고리이므로 기본값이 15일 후로 설정되었습니다."
        else:
            default_expiry = datetime.today() + pd.DateOffset(years=10)
            help_text = "일반 카테고리이므로 기본값이 10년 후로 설정되었습니다."

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
                        st.error("카테고리를 선택해 주세요.")
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
                        "카테고리 변경", 
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

elif menu == "카테고리 설정":
    st.title("⚙️ 카테고리 관리")
    
    tab_loc1, tab_loc2 = st.tabs(["카테고리 등록", "카테고리 수정/삭제"])
    
    with tab_loc1:
        st.subheader("새 카테고리 등록")
        with st.form("add_loc_form"):
            new_loc_name = st.text_input("카테고리 이름 (예: 냉장실, 거실 서랍 등)")
            
            # Get unique existing categories
            locs_raw = db.get_locations()
            existing_categories = sorted(list(set([loc[2] for loc in locs_raw])))
            
            cat_options = ["(카테고리 이름과 동일)"] + existing_categories + ["직접 입력"]
            selected_cat = st.selectbox("대분류 선택", cat_options)
            
            custom_cat = ""
            if selected_cat == "직접 입력":
                custom_cat = st.text_input("새 대분류명 입력")
            
            is_food_check = st.checkbox("식료품 카테고리인가요?", help="체크 시 이 카테고리에 물품 등록 시 유통기한 기본값이 15일로 설정됩니다.")
            
            if st.form_submit_button("카테고리 등록"):
                if new_loc_name:
                    final_cat = new_loc_name
                    if selected_cat == "직접 입력":
                        final_cat = custom_cat if custom_cat else new_loc_name
                    elif selected_cat != "(카테고리 이름과 동일)":
                        final_cat = selected_cat
                    
                    db.add_location(new_loc_name, final_cat, None, is_food_check)
                    st.success(f"'{new_loc_name}' ({final_cat}) 등록 완료!")
                    st.rerun()
                else:
                    st.error("카테고리 이름을 입력해 주세요.")
    
    with tab_loc2:
        st.subheader("등록된 카테고리 관리")
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
            selected_loc_id = st.selectbox("관리할 카테고리 선택", options=loc_df['id'].tolist(), 
                                      format_func=lambda x: f"[{loc_df[loc_df['id']==x]['category'].iloc[0]}] {loc_df[loc_df['id']==x]['name'].iloc[0]}")
            
            loc_to_edit = db.get_location_by_id(selected_loc_id)
            # loc_to_edit: tuple (id, name, cat, parent, is_food)
            
            with st.form("edit_loc_form"):
                st.markdown(f"**'{loc_to_edit[1]}'** 수정 중")
                u_loc_name = st.text_input("카테고리 이름", value=loc_to_edit[1])
                u_loc_cat = st.text_input("대분류", value=loc_to_edit[2]) 
                u_is_food = st.checkbox("식료품 카테고리", value=bool(loc_to_edit[4]) if len(loc_to_edit)>4 else False)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("수정 저장"):
                        db.update_location(selected_loc_id, u_loc_name, u_loc_cat, u_is_food)
                        st.success("카테고리 정보가 수정되었습니다.")
                        st.rerun()
                with c2:
                    if st.form_submit_button("🗑️ 카테고리 삭제"):
                        db.delete_location_safely(selected_loc_id)
                        st.warning("카테고리가 삭제되었습니다.")
                        st.rerun()
        else:
            st.info("등록된 카테고리가 없습니다.")

elif menu == "영수증 관리":
    st.title("🧾 영수증 관리")
    
    tab_receipt1, tab_receipt2 = st.tabs(["영수증 등록", "영수증 목록 및 관리"])
    
    with tab_receipt1:
        st.subheader("새 영수증 등록")
        
        # Category Selection Moved OUTSIDE the form to trigger rerun
        locations = db.get_locations()
        if locations:
            loc_options = {f"[{loc[2]}] {loc[1]}": loc for loc in locations}
            selected_loc_label = st.selectbox("카테고리 선택", list(loc_options.keys()), key="receipt_cat")
            selected_loc = loc_options[selected_loc_label]
            category_id = selected_loc[0]
        else:
            st.warning("등록된 카테고리가 없습니다. '카테고리 설정'에서 카테고리를 먼저 등록해 주세요.")
            category_id = None
            
        st.markdown("---")
        st.write("이미지를 업로드하거나 직접 촬영하여 등록할 수 있습니다.")
        
        input_tab1, input_tab2 = st.tabs(["📁 파일 업로드", "📷 카메라 촬영"])
        
        with input_tab1:
            uploaded_file = st.file_uploader("영수증 이미지 (JPG)", type=['jpg', 'jpeg'], key="receipt_upload_file")
        
        with input_tab2:
            camera_file = st.camera_input("영수증 촬영", key="receipt_camera_input")
            
        # Combine inputs: Prefer camera if both exist, or use whichever is provided
        uploaded_image = camera_file if camera_file is not None else uploaded_file
        
        image_path = None
        if uploaded_image is not None:
            st.image(uploaded_image, caption="선택된 영수증 이미지", use_container_width=True)
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"receipt_{timestamp}.jpg"
            image_path = os.path.join("uploads", filename)
            
            if st.button("🖼️ 이미지 분석 (OCR) 실행"):
                with st.spinner("이미지를 분석하고 있습니다..."):
                    with open(image_path, "wb") as f:
                        f.write(uploaded_image.getbuffer())
                    
                    text, info = ocr_helper.extract_receipt_info(image_path)
                    st.session_state['ocr_text'] = text
                    st.session_state['ocr_store'] = info.get('store_name', '')
                    st.session_state['ocr_address'] = info.get('store_address', '')
                    st.session_state['ocr_amount'] = info.get('total_amount', 0.0)
                    st.session_state['ocr_sales'] = info.get('sales_amount', 0.0)
                    st.session_state['ocr_date'] = info.get('use_date')
                    st.session_state['ocr_card'] = info.get('card_type', '')
                    st.session_state['ocr_card_num'] = info.get('card_number', '')
                    st.session_state['ocr_vat'] = info.get('vat', 0.0)
                    st.rerun()

        with st.form("add_receipt_form"):
            col1, col2 = st.columns(2)
            with col1:
                store_name = st.text_input("사용처 (필수)", value=st.session_state.get('ocr_store', ''))
                card_type = st.text_input("카드종류 (예: 신한카드, 현대카드 등)", value=st.session_state.get('ocr_card', ''))
                
                default_date = datetime.today()
                ocr_date_str = st.session_state.get('ocr_date')
                if ocr_date_str:
                    try:
                        default_date = pd.to_datetime(ocr_date_str).date()
                    except:
                        pass
                use_date = st.date_input("사용일시", value=default_date)
                
                default_sales = float(st.session_state.get('ocr_sales', 0.0))
                sales_amount = st.number_input("판매금액", min_value=0.0, step=100.0, value=default_sales)
            with col2:
                store_address = st.text_input("사용처주소", value=st.session_state.get('ocr_address', ''))
                card_number = st.text_input("카드번호 (예: 1234-****-****-****)", value=st.session_state.get('ocr_card_num', ''))
                
                default_vat = float(st.session_state.get('ocr_vat', 0.0))
                vat = st.number_input("부가세", min_value=0.0, step=10.0, value=default_vat)
                
                default_amount = float(st.session_state.get('ocr_amount', 0.0))
                total_amount = st.number_input("합계금액", min_value=0.0, step=100.0, value=default_amount)
            
            notes = st.text_area("참고사항 (OCR 결과가 여기에 표시됩니다)", value=st.session_state.get('ocr_text', ''))
            
            if st.form_submit_button("영수증 등록"):
                if store_name:
                    if category_id:
                        final_image_path = ""
                        if uploaded_image is not None and image_path:
                            if not os.path.exists(image_path):
                                with open(image_path, "wb") as f:
                                    f.write(uploaded_image.getbuffer())
                            final_image_path = image_path
                            
                        db.add_receipt(category_id, store_name, store_address, card_type, card_number, use_date.isoformat(), sales_amount, vat, total_amount, notes, final_image_path)
                        st.success("영수증이 등록되었습니다!")
                        st.balloons()
                        
                        # Clear OCR session state
                        for k in ['ocr_text', 'ocr_store', 'ocr_address', 'ocr_amount', 'ocr_sales', 'ocr_date', 'ocr_card', 'ocr_card_num', 'ocr_vat']:
                            if k in st.session_state:
                                del st.session_state[k]
                    else:
                        st.error("카테고리를 선택해 주세요.")
                else:
                    st.error("사용처를 입력해 주세요.")
                    
    with tab_receipt2:
        st.subheader("영수증 목록 및 관리")
        
        locations_dict = {loc[0]: f"[{loc[2]}] {loc[1]}" for loc in db.get_locations()}
        receipts = db.get_receipts()
        
        if receipts:
            # Prepare DataFrame
            data = []
            for r in receipts:
                # r: id(0), cat_id(1), store_name(2), addr(3), card_type(4), card_number(5), use_date(6), 
                # sales_amt(7), vat(8), total_amt(9), notes(10), img_path(11)
                data.append({
                    "id": r[0],
                    "카테고리": locations_dict.get(r[1], "알 수 없음"),
                    "사용처": r[2],
                    "사용일시": r[6],
                    "합계금액": f"{r[9]:,.0f}원",
                    "카드종류": r[4],
                    "category_id": r[1]
                })
            df = pd.DataFrame(data)
            
            # 카테고리 필터링
            all_cats = ["전체"] + sorted(list(set(df["카테고리"].tolist())))
            filter_cat = st.selectbox("카테고리로 필터링", all_cats)
            
            if filter_cat != "전체":
                filtered_df = df[df["카테고리"] == filter_cat]
            else:
                filtered_df = df
                
            st.dataframe(filtered_df.drop(columns=['id', 'category_id']), use_container_width=True)
            
            st.divider()
            
            if not filtered_df.empty:
                st.write("📝 영수증 상세/수정 및 삭제")
                
                selected_receipt_id = st.selectbox(
                    "관리할 영수증 선택", 
                    options=filtered_df['id'].tolist(),
                    format_func=lambda x: f"{filtered_df[filtered_df['id']==x]['사용처'].iloc[0]} ({filtered_df[filtered_df['id']==x]['사용일시'].iloc[0]})"
                )
                
                # Fetch detailed data
                r_idx = next(i for i, r in enumerate(receipts) if r[0] == selected_receipt_id)
                item_data = receipts[r_idx]
                
                if item_data[11] and os.path.exists(item_data[11]):
                    st.image(item_data[11], caption=f"이미지: {item_data[11]}", width=300)
                
                with st.form(f"edit_receipt_form_{selected_receipt_id}"):
                    # Update Location options in Edit
                    loc_edit_keys = list(locations_dict.values())
                    current_loc_val = locations_dict.get(item_data[1])
                    u_cat_idx = loc_edit_keys.index(current_loc_val) if current_loc_val in loc_edit_keys else 0
                    
                    u_cat_label = st.selectbox("카테고리 변경", options=loc_edit_keys, index=u_cat_idx)
                    u_cat_id = next((k for k, v in locations_dict.items() if v == u_cat_label), item_data[1])
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        u_store = st.text_input("사용처", value=item_data[2])
                        u_card_type = st.text_input("카드종류", value=item_data[4] or "")
                        u_date = st.date_input("사용일시", value=pd.to_datetime(item_data[6]).date())
                        u_sales = st.number_input("판매금액", value=float(item_data[7]), step=100.0)
                    with c2:
                        u_addr = st.text_input("사용처주소", value=item_data[3] or "")
                        u_card_num = st.text_input("카드번호", value=item_data[5] or "")
                        u_vat = st.number_input("부가세", value=float(item_data[8]), step=10.0)
                        u_total = st.number_input("합계금액", value=float(item_data[9]), step=100.0)
                        
                    u_notes = st.text_area("참고사항", value=item_data[10] or "")
                    
                    btn1, btn2, _ = st.columns([1, 1, 2])
                    with btn1:
                        if st.form_submit_button("💾 수정 사항 저장"):
                            db.update_receipt(selected_receipt_id, u_cat_id, u_store, u_addr, u_card_type, u_card_num, u_date.isoformat(), u_sales, u_vat, u_total, u_notes, item_data[11])
                            st.success("영수증이 수정되었습니다!")
                            st.rerun()
                    with btn2:
                        if st.form_submit_button("🗑️ 영수증 삭제"):
                            # Optionally delete the file as well
                            if item_data[11] and os.path.exists(item_data[11]):
                                try:
                                    os.remove(item_data[11])
                                except:
                                    pass
                            db.delete_receipt(selected_receipt_id)
                            st.warning("삭제되었습니다.")
                            st.rerun()
        else:
            st.info("등록된 영수증이 없습니다.")

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

elif menu == "데이터 관리":
    st.title("💾 데이터 관리 (관리자 전용)")
    
    tab1, tab2 = st.tabs(["데이터 내보내기 (Export)", "데이터 가져오기 (Import)"])
    
    with tab1:
        st.subheader("Excel 파일로 다운로드")
        st.info("현재 등록된 모든 카테고리와 물품 데이터를 Excel 파일로 저장합니다.")
        
        if st.button("데이터 조회 및 변환"):
            loc_df, item_df, receipt_df = db.export_all_data()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**카테고리 데이터** ({len(loc_df)}건)")
                st.dataframe(loc_df.head(), use_container_width=True)
                
                try:
                    import io
                    buffer_loc = io.BytesIO()
                    with pd.ExcelWriter(buffer_loc, engine='openpyxl') as writer:
                        loc_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 카테고리(locations) 다운로드",
                        data=buffer_loc.getvalue(),
                        file_name="mycatalog_locations.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    st.error("openpyxl 라이브러리가 설치되지 않아 Excel 생성이 불가능합니다.")

            with col2:
                st.write(f"**물품 데이터** ({len(item_df)}건)")
                st.dataframe(item_df.head(), use_container_width=True)
                
                try:
                    import io
                    buffer_item = io.BytesIO()
                    with pd.ExcelWriter(buffer_item, engine='openpyxl') as writer:
                        item_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 물품(items) 다운로드",
                        data=buffer_item.getvalue(),
                        file_name="mycatalog_items.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    pass

            with col3:
                st.write(f"**영수증 데이터** ({len(receipt_df)}건)")
                st.dataframe(receipt_df.head(), use_container_width=True)
                
                try:
                    import io
                    buffer_receipt = io.BytesIO()
                    with pd.ExcelWriter(buffer_receipt, engine='openpyxl') as writer:
                        receipt_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 영수증(receipts) 다운로드",
                        data=buffer_receipt.getvalue(),
                        file_name="mycatalog_receipts.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    pass

    with tab2:
        st.subheader("Excel 파일 업로드 (데이터 교체)")
        st.warning("⚠️ 주의: 데이터를 업로드하면 **해당 항목의 기존 데이터가 모두 삭제**되고 업로드한 데이터로 대체됩니다. 복구할 수 없으니 신중하게 진행해 주세요.")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("### 1. 카테고리 (Locations)")
            uploaded_loc = st.file_uploader("locations.xlsx 파일 선택", type=['xlsx'], key="upload_loc")
            if uploaded_loc:
                if st.button("🚀 카테고리 데이터 덮어쓰기", type="primary"):
                    try:
                        new_loc_df = pd.read_excel(uploaded_loc)
                        req_loc_cols = {'name', 'category'}
                        if not req_loc_cols.issubset(new_loc_df.columns):
                            st.error(f"필수 컬럼 누락: {req_loc_cols - set(new_loc_df.columns)}")
                        else:
                            success, msg = db.import_locations(new_loc_df)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
                    except Exception as e:
                        st.error(f"오류: {e}")
            
        with c2:
            st.markdown("### 2. 물품 (Items)")
            uploaded_item = st.file_uploader("items.xlsx 파일 선택", type=['xlsx'], key="upload_item")
            if uploaded_item:
                if st.button("🚀 물품 데이터 덮어쓰기", type="primary"):
                    try:
                        new_item_df = pd.read_excel(uploaded_item)
                        req_item_cols = {'name', 'quantity'}
                        if not req_item_cols.issubset(new_item_df.columns):
                            st.error(f"필수 컬럼 누락: {req_item_cols - set(new_item_df.columns)}")
                        else:
                            success, msg = db.import_items(new_item_df)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
                    except Exception as e:
                        st.error(f"오류: {e}")

        with c3:
            st.markdown("### 3. 영수증 (Receipts)")
            uploaded_receipt = st.file_uploader("receipts.xlsx 파일 선택", type=['xlsx'], key="upload_receipt")
            if uploaded_receipt:
                if st.button("🚀 영수증 데이터 덮어쓰기", type="primary"):
                    try:
                        new_receipt_df = pd.read_excel(uploaded_receipt)
                        req_receipt_cols = {'store_name'}
                        if not req_receipt_cols.issubset(new_receipt_df.columns):
                            st.error(f"필수 컬럼 누락: {req_receipt_cols - set(new_receipt_df.columns)}")
                        else:
                            success, msg = db.import_receipts(new_receipt_df)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
                    except Exception as e:
                        st.error(f"오류: {e}")
