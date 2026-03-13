import os
import json
import sys
from PIL import Image

try:
    # 최신 SDK 사용 (Deprecated 경고 해결)
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

def extract_receipt_info(image_file):
    """
    Extracts text and key information from a receipt image using Google Gemini AI (Latest SDK).
    Returns: (raw_response_text, info_dict)
    """
    if genai is None:
        return ("'google-genai' 패키지가 설치되지 않았습니다. 터미널에서 'pip install google-genai'를 실행해 주세요.", {})
    
    # API 키 찾기 (순서: os.environ -> streamlit secrets)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except:
            pass
            
    if not api_key:
        return ("Gemini API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일에 'GEMINI_API_KEY'를 추가해 주세요.", {})

    try:
        # 클라이언트 초기화 (최신 방식)
        client = genai.Client(api_key=api_key)
        
        # 모델명 설정
        model_name = 'models/gemini-flash-latest' # 최신 모델로 업그레이드
        
        # 이미지 로드 및 검증 
        img = Image.open(image_file)
        
        # prompt = """
        # 영수증 이미지에서 다음 정보를 추출하여 정확한 JSON 형식으로 답변해줘.
        # 추출할 정보:
        # - store_name (상호명/가맹점명)
        # - card_type (카드사 종류, 예: 신한카드, 현대카드 등)
        # - use_date (결제일시, YYYY-MM-DD 형식)
        # - total_amount (합계금액/결제금액, 숫자만)
        # - vat (부가세, 숫자만)
        # - full_text (영수증에 적힌 전체 텍스트 요약)

        # JSON 결과 외에 다른 설명은 생략하고 순수 JSON 데이터만 반환해줘.
        # """
        prompt = """
        이 영수증 이미지를 분석하여 반드시 아래 JSON 형식으로만 반환하세요. 
        키 이름을 절대 변경하지 마세요.

        {"store_name":"상호명","store_address":"주소","card_type":"카드종류","card_number":"카드번호","transaction_datetime":"승인일시(YYYY/MM/DD HH:MM:SS형식)","sale_amount":"판매금액","vat_amount":"부가세","total_amount":"합계금액"}
        """

        # 실행 (최신 SDK 호출 방식)
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, img]
        )
        
        if not response or not response.text:
            return "Gemini 응답 생성에 실패했습니다. (응답 없음)", {}
            
        response_text = response.text.strip()
        
        # JSON 파싱 (마크다운 대응 및 유연한 파싱)
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        json_str = json_str.replace('\n', ' ').strip()
        try:
            info_extracted = json.loads(json_str)
        except json.JSONDecodeError:
            # 보수적인 파싱 실패 시 raw text 반환
            return f"JSON 파싱 실패: {response_text}", {}

        # 숫자 정제 함수
        def clean_float(val):
            if val is None: return 0.0
            try:
                # 숫자 외 문자 제거 및 소수점 처리
                clean_val = "".join(c for c in str(val) if c.isdigit() or c == '.')
                return float(clean_val) if clean_val else 0.0
            except:
                return 0.0

        # 사용자 요청 필드명과 앱 내부 필드명 매핑
        info = {
            'store_name': info_extracted.get('store_name', ''),
            'store_address': info_extracted.get('store_address', ''),
            'card_type': info_extracted.get('card_type', ''),
            'card_number': info_extracted.get('card_number', ''),
            'use_date': info_extracted.get('transaction_datetime'),
            'total_amount': clean_float(info_extracted.get('total_amount')),
            'sales_amount': clean_float(info_extracted.get('sale_amount')), # prompt의 sale_amount 매핑
            'vat': clean_float(info_extracted.get('vat_amount')) # prompt의 vat_amount 매핑
        }
        
        display_text = response_text # 원본 응답을 참고용으로 보냄
        return display_text, info

    except Exception as e:
        # 모델 미지원 등으로 실패 시 gemini-1.5-flash로 시도하는 fallback
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            try:
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[prompt, img]
                )
                if response and response.text:
                    # 동일한 파싱 로직 적용 (중복 방지를 위해 실제 구현 시엔 함수화 권장)
                    # 여기서는 단순화를 위해 메시지만 안내하거나 기본 에러를 반환
                    return f"최신 모델(2.0) 미지원으로 1.5로 재시도 필요: {error_msg}", {}
            except:
                pass
        return f"Gemini API (신규 SDK) 처리 중 오류 발생: {error_msg}", {}
