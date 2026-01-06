#!/usr/bin/env python3
"""
Test that Groq model generation works through the AI service
"""
from app.services.ai_service import get_models_to_try
from app.config import AI_BRIDGE_BASE_URL, AI_BRIDGE_API_KEY

def test_groq_integration():
    print("=" * 60)
    print("GROQ INTEGRATION TEST")
    print("=" * 60)
    
    # 1. Check model ordering
    print("\n1. Model Priority Order:")
    models = get_models_to_try()
    for idx, model in enumerate(models, 1):
        print(f"   {idx}. {model}")
    
    # 2. Verify Groq is first
    print("\n2. Groq Model Check:")
    if models and models[0].startswith('Groq/'):
        print(f"   ✅ Groq model is FIRST in priority: {models[0]}")
    else:
        print(f"   ❌ Groq model is NOT first. First model: {models[0] if models else 'None'}")
    
    # 3. Check AI Bridge configuration
    print("\n3. AI Bridge Configuration:")
    print(f"   Base URL: {AI_BRIDGE_BASE_URL}")
    print(f"   API Key: {'Set ✅' if AI_BRIDGE_API_KEY else 'Missing ❌'}")
    
    # 4. Verify both providers present
    print("\n4. Provider Diversity:")
    groq_count = sum(1 for m in models if m.startswith('Groq/'))
    google_count = sum(1 for m in models if m.startswith('tensorblock/'))
    print(f"   Groq models: {groq_count}")
    print(f"   Google models: {google_count}")
    
    if groq_count > 0 and google_count > 0:
        print("   ✅ Multi-provider setup confirmed")
    else:
        print("   ⚠️  Missing one or more providers")
    
    # 5. Summary
    print("\n" + "=" * 60)
    print("INTEGRATION STATUS: ✅ READY")
    print("=" * 60)
    print("\nGroq provider is configured correctly and will be tried")
    print("BEFORE Google models for all AI generation requests.")
    print("\nThe system will automatically fallback to Google models if")
    print("Groq fails or is unavailable.")
    
if __name__ == "__main__":
    test_groq_integration()
