#!/usr/bin/env python3
"""
Check LLM models in database
"""
from app.db.db_factory import DatabaseFactory
from app.services.llm_service import llm_service

def check_llm_models():
    db = DatabaseFactory.get_provider()
    conn = db._get_connection()
    cursor = conn.cursor()
    
    # Check all models
    cursor.execute("""
        SELECT id, model_name, display_name, provider, model_type, version,
               order_number, active, deprecated, manual, last_seen_at
        FROM llm_models
        ORDER BY order_number ASC
    """)
    
    print("=== All LLM Models in Database ===\n")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"  Model Name: {row[1]}")
        print(f"  Display Name: {row[2]}")
        print(f"  Provider: {row[3]}")
        print(f"  Type: {row[4]}, Version: {row[5]}")
        print(f"  Order: {row[6]}, Active: {row[7]}, Deprecated: {row[8]}, Manual: {row[9]}")
        print(f"  Last Seen: {row[10]}")
        print()
    
    print(f"\nTotal models: {len(rows)}")
    
    # Check active models
    cursor.execute("""
        SELECT COUNT(*) FROM llm_models WHERE active = TRUE
    """)
    active_count = cursor.fetchone()[0]
    print(f"Active models: {active_count}")
    
    # Check Groq models specifically
    cursor.execute("""
        SELECT model_name, active, deprecated, order_number
        FROM llm_models
        WHERE provider = 'groq'
        ORDER BY order_number ASC
    """)
    
    print("\n=== Groq Models ===")
    groq_rows = cursor.fetchall()
    if groq_rows:
        for row in groq_rows:
            print(f"  {row[0]} - Active: {row[1]}, Deprecated: {row[2]}, Order: {row[3]}")
    else:
        print("  No Groq models found")
    
    cursor.close()
    conn.close()
    
    # Test the llm_service methods
    print("\n=== Testing llm_service.get_ordered_forge_models() ===")
    forge_models = llm_service.get_ordered_forge_models(force_refresh=True)
    if forge_models:
        for idx, model in enumerate(forge_models):
            print(f"  {idx+1}. {model}")
    else:
        print("  No models returned")
    
    print("\n=== Testing llm_service.get_active_models('groq') ===")
    groq_models = llm_service.get_active_models('groq')
    if groq_models:
        for model in groq_models:
            print(f"  {model['model_name']} (Order: {model['order_number']})")
    else:
        print("  No active Groq models")

if __name__ == "__main__":
    check_llm_models()
