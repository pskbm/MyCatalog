import re

with open('C:/Coding/MyCatalog/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace strings
content = content.replace('보관 장소', '카테고리')
content = content.replace('보관장소', '카테고리')
content = content.replace('장소 이름', '카테고리 이름')
content = content.replace('장소가', '카테고리가')
content = content.replace('장소를', '카테고리를')
content = content.replace('새 장소', '새 카테고리')
content = content.replace('등록된 장소', '등록된 카테고리')
content = content.replace('장소 삭제', '카테고리 삭제')

# Fix menu options to include "영수증 관리"
content = content.replace('menu_options = ["대시보드", "물품 관리", "카테고리 설정", "알림 센터"]', 'menu_options = ["대시보드", "물품 관리", "영수증 관리", "카테고리 설정", "알림 센터"]')

with open('C:/Coding/MyCatalog/app.py', 'w', encoding='utf-8') as f:
    f.write(content)
