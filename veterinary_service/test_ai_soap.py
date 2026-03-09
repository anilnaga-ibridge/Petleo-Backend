import os
import json
import urllib.request
from dotenv import load_dotenv

# Mocking the service structure for standalone test
class MockAIService:
    @staticmethod
    def format_soap_notes(raw_notes):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return "Error: No API Key found"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = f"Format these veterinary notes to SOAP: {raw_notes}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            req.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            return f"Error: {e}"

def test():
    load_dotenv()
    notes = "Dog Bella, 5yo Lab. Owner says she's been scratching ears for 3 days. Ears are red and have brown discharge. Suspect yeast infection. prescribed Otic solution twice daily for 1 week. Recheck in 10 days."
    print("Testing AI Format...")
    print(f"Input: {notes}")
    result = MockAIService.format_soap_notes(notes)
    print("\nResult:\n")
    print(result)

if __name__ == "__main__":
    test()
