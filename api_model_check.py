# Python SDK 기준 확인 코드
import google.generativeai as genai

genai.configure(api_key="AIzaSyC0bFssaDsnpvTKLXcBoSYpRXsaStN1X74")

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)