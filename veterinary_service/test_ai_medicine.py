import os
import django
import sys
import json

# Setup Django Environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.services import AIService
from dotenv import load_dotenv

load_dotenv()

def test_suggestions():
    print(f"API KEY: {os.environ.get('GEMINI_API_KEY')}")
    print("Testing AI Medicine Suggestions API...\n")
    
    query = "Amoxi"
    print(f"Querying for: '{query}'")
    
    results = AIService.suggest_prescription_details(query)
    
    print("\n--- RESULTS ---")
    print(json.dumps(results, indent=2))
    
    assert len(results) > 0, "No results returned from Gemini!"
    assert 'medicine_name' in results[0], "Missing medicine_name key"
    assert 'dosage' in results[0], "Missing dosage key"
    assert 'frequency' in results[0], "Missing frequency key"
    
    print("\n✅ Auto-complete Suggestion API is working correctly!")

if __name__ == '__main__':
    test_suggestions()
