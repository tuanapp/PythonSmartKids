#!/usr/bin/env python3
"""
Update Groq model display name to be more user-friendly
"""
from app.db.db_factory import DatabaseFactory

def update_groq_display_name():
    db = DatabaseFactory.get_provider()
    conn = db._get_connection()
    cursor = conn.cursor()
    
    # Update the display name for Groq model
    cursor.execute("""
        UPDATE llm_models
        SET display_name = 'Llama 3.3 70B Versatile',
            model_type = 'llama',
            version = '3.3'
        WHERE provider = 'groq' AND model_name = 'llama-3.3-70b-versatile'
        RETURNING id, model_name, display_name, provider, model_type, version
    """)
    
    result = cursor.fetchone()
    conn.commit()
    
    if result:
        print("✅ Updated Groq model:")
        print(f"   ID: {result[0]}")
        print(f"   Model Name: {result[1]}")
        print(f"   Display Name: {result[2]}")
        print(f"   Provider: {result[3]}")
        print(f"   Type: {result[4]}, Version: {result[5]}")
    else:
        print("❌ No Groq model found to update")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    update_groq_display_name()
