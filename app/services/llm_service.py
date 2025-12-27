"""
LLM Service for managing AI models across providers.

Handles:
- Fetching and syncing models from provider APIs
- Managing model status (active, deprecated, manual)
- Resolving model names to IDs for FK references
- Generating Forge-compatible model names from provider-native names
- Providing ordered list of models for AI generation (with caching)
"""
import logging
import requests
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from app.db.db_factory import DatabaseFactory
from app.config import NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST

logger = logging.getLogger(__name__)

# =============================================================================
# Model Cache Configuration
# =============================================================================
# Cache for ordered Forge models (24-hour TTL)
CACHE_TTL_SECONDS = 86400  # 24 hours

_models_cache: Optional[List[str]] = None
_cache_timestamp: float = 0.0


# Extensible list of supported providers
# Add new providers here with their API configuration
SUPPORTED_PROVIDERS = {
    'google': {
        'name': 'Google',
        'forge_prefix': 'tensorblock',  # TensorBlock Forge format: "tensorblock/gemini-2.0-flash"
        'model_name_strip': 'models/',   # Strip this prefix from model_name before formatting
        'api_url_template': 'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}',
        'env_key': 'GOOGLE_API_KEY',
    },
    'groq': {
        'name': 'Groq',
        'forge_prefix': 'Groq',  # Prefix used in Forge: "Groq/llama-3.3-70b-versatile"
        'api_url_template': 'https://api.groq.com/openai/v1/models',
        'env_key': 'GROQ_API_KEY',
        'auth_header': 'Authorization',
        'auth_format': 'Bearer {api_key}',
    },
    'anthropic': {
        'name': 'Anthropic',
        'forge_prefix': 'Anthropic',
        'api_url_template': 'https://api.anthropic.com/v1/models',
        'env_key': 'ANTHROPIC_API_KEY',
        'auth_header': 'x-api-key',
        'auth_format': '{api_key}',
    },
    'openai': {
        'name': 'OpenAI',
        'forge_prefix': 'OpenAI',
        'api_url_template': 'https://api.openai.com/v1/models',
        'env_key': 'OPENAI_API_KEY',
        'auth_header': 'Authorization',
        'auth_format': 'Bearer {api_key}',
    },
}


class LLMService:
    """Service for managing LLM models across providers."""
    
    def __init__(self):
        self.db_provider = DatabaseFactory.get_provider()
    
    def _get_connection(self):
        """Get a database connection."""
        return self.db_provider._get_connection()
    
    # =========================================================================
    # Public API Methods
    # =========================================================================
    
    def get_active_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active LLM models, optionally filtered by provider.
        
        Args:
            provider: Optional provider filter ('google', 'groq', etc.)
        
        Returns:
            List of active models ordered by order_number
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if provider:
                cursor.execute("""
                    SELECT id, model_name, display_name, provider, model_type, version,
                           order_number, active, deprecated, manual, last_seen_at,
                           created_at, updated_at
                    FROM llm_models
                    WHERE active = TRUE AND provider = %s
                    ORDER BY order_number ASC
                """, (provider,))
            else:
                cursor.execute("""
                    SELECT id, model_name, display_name, provider, model_type, version,
                           order_number, active, deprecated, manual, last_seen_at,
                           created_at, updated_at
                    FROM llm_models
                    WHERE active = TRUE
                    ORDER BY order_number ASC
                """)
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [self._row_to_model_dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching active models: {e}")
            raise
    
    def get_ordered_forge_models(self, force_refresh: bool = False) -> List[str]:
        """
        Get ordered list of active, non-deprecated models formatted as Forge API names.
        
        Results are cached for 24 hours (CACHE_TTL_SECONDS) to avoid DB queries on every AI call.
        
        Args:
            force_refresh: If True, bypass cache and query database
        
        Returns:
            List of Forge-formatted model names, e.g., ['tensorblock/gemini-2.0-flash', 'Groq/llama-3.3-70b-versatile']
            Returns empty list if no models available or on error.
        
        Example:
            models = llm_service.get_ordered_forge_models()
            # Returns: ['tensorblock/gemini-2.0-flash', 'Groq/llama-3.3-70b-versatile', ...]
        """
        global _models_cache, _cache_timestamp
        
        current_time = time.time()
        cache_age = current_time - _cache_timestamp
        
        # Return cached models if valid and not force refresh
        if not force_refresh and _models_cache is not None and cache_age < CACHE_TTL_SECONDS:
            logger.debug(f"Using cached models list (age: {int(cache_age)}s, count: {len(_models_cache)})")
            return _models_cache
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Query active, non-deprecated models ordered by order_number
            cursor.execute("""
                SELECT model_name, provider
                FROM llm_models
                WHERE active = TRUE AND deprecated = FALSE
                ORDER BY order_number ASC
            """)
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Format as Forge API names using SUPPORTED_PROVIDERS mapping
            forge_models = []
            for model_name, provider in rows:
                provider_config = SUPPORTED_PROVIDERS.get(provider)
                if provider_config:
                    # Add provider prefixes back when retrieving from DB
                    if provider == 'google':
                        forge_name = f"tensorblock/{model_name}"
                    else:
                        forge_prefix = provider_config['forge_prefix']
                        forge_name = f"{forge_prefix}/{model_name}"
                    forge_models.append(forge_name)
                else:
                    # Unknown provider - skip with warning
                    logger.warning(f"Unknown provider '{provider}' for model '{model_name}', skipping")
            
            # Update cache
            _models_cache = forge_models
            _cache_timestamp = current_time
            
            logger.info(f"Loaded {len(forge_models)} models from database (cache refreshed)")
            return forge_models
            
        except Exception as e:
            logger.error(f"Error fetching ordered Forge models: {e}")
            # Return empty list on error - caller should use fallback
            return []
    
    def get_model_id_by_name(self, model_name: str) -> Optional[int]:
        """
        Look up model ID by model_name.
        
        Handles both provider-native names (e.g., 'models/gemini-2.0-flash')
        and Forge-formatted names (e.g., 'tensorblock/gemini-2.0-flash').
        
        Args:
            model_name: The model name to look up
        
        Returns:
            Model ID if found, None otherwise
        """
        try:
            # Strip prefixes to get the clean model name as stored in DB
            clean_name = model_name
            
            # Strip Forge prefixes
            for provider_config in SUPPORTED_PROVIDERS.values():
                prefix = provider_config['forge_prefix'] + '/'
                if clean_name.startswith(prefix):
                    clean_name = clean_name[len(prefix):]
                    break
            
            # Strip provider-native prefixes (e.g., 'models/' for Google)
            if clean_name.startswith('models/'):
                clean_name = clean_name[len('models/'):]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM llm_models WHERE model_name = %s
            """, (clean_name,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error looking up model ID for '{model_name}': {e}")
            return None
    
    def update_model(self, model_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an LLM model's properties.
        
        Args:
            model_name: The model_name to update (can include prefixes, will be stripped)
            updates: Dict with fields to update (order_number, active, manual, display_name)
        
        Returns:
            Updated model dict or error
        """
        try:
            # Strip prefixes to get the clean model name as stored in DB
            clean_name = model_name
            
            # Strip Forge prefixes
            for provider_config in SUPPORTED_PROVIDERS.values():
                prefix = provider_config['forge_prefix'] + '/'
                if clean_name.startswith(prefix):
                    clean_name = clean_name[len(prefix):]
                    break
            
            # Strip provider-native prefixes (e.g., 'models/' for Google)
            if clean_name.startswith('models/'):
                clean_name = clean_name[len('models/'):]
            
            # Build dynamic update query
            allowed_fields = {'order_number', 'active', 'manual', 'display_name'}
            update_fields = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
            
            if not update_fields:
                return {'success': False, 'error': 'No valid fields to update'}
            
            # Add updated_at
            update_fields['updated_at'] = datetime.now()
            
            set_clause = ', '.join([f"{k} = %s" for k in update_fields.keys()])
            values = list(update_fields.values()) + [clean_name]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                UPDATE llm_models
                SET {set_clause}
                WHERE model_name = %s
                RETURNING id, model_name, display_name, provider, model_type, version,
                          order_number, active, deprecated, manual, last_seen_at,
                          created_at, updated_at
            """, values)
            
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            if result:
                return {'success': True, 'model': self._row_to_model_dict(result)}
            else:
                return {'success': False, 'error': f"Model '{model_name}' not found"}
                
        except Exception as e:
            logger.error(f"Error updating model '{model_name}': {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_models_from_provider(self, provider: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync models from a provider's API.
        
        Logic:
        - Fetch current models from provider API
        - For each model in API response:
          - If exists with manual=true: skip (don't touch)
          - If exists with manual=false: update last_seen_at
          - If new: insert with active=true, deprecated=false, manual=false
        - For models in DB not in API response (and manual=false):
          - Set active=false, deprecated=true
        
        Args:
            provider: Provider key ('google', 'groq', etc.)
            api_key: Optional API key (uses env var if not provided)
        
        Returns:
            Sync result with counts of added/updated/deprecated models
        """
        if provider not in SUPPORTED_PROVIDERS:
            return {
                'success': False,
                'provider': provider,
                'models_added': 0,
                'models_updated': 0,
                'models_deprecated': 0,
                'message': f"Unsupported provider: {provider}. Supported: {list(SUPPORTED_PROVIDERS.keys())}"
            }
        
        try:
            # Fetch models from provider API
            models_from_api = self._fetch_models_from_provider(provider, api_key)
            
            if models_from_api is None:
                return {
                    'success': False,
                    'provider': provider,
                    'models_added': 0,
                    'models_updated': 0,
                    'models_deprecated': 0,
                    'message': f"Failed to fetch models from {provider} API"
                }
            
            logger.info(f"Fetched {len(models_from_api)} models from {provider}")
            
            # Get current models from DB for this provider
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT model_name, manual FROM llm_models WHERE provider = %s
            """, (provider,))
            
            existing_models = {row[0]: row[1] for row in cursor.fetchall()}
            
            models_added = 0
            models_updated = 0
            now = datetime.now()
            
            # Extract model names from API response
            api_model_names = set()
            
            for idx, model_info in enumerate(models_from_api):
                model_name = model_info['model_name']
                api_model_names.add(model_name)
                
                # Strip provider prefixes when storing in DB
                if provider == 'google' and model_name.startswith('models/'):
                    stored_model_name = model_name[len('models/'):]
                else:
                    stored_model_name = model_name
                
                if stored_model_name in existing_models:
                    # Model exists
                    if existing_models[stored_model_name]:
                        # manual=True, skip
                        logger.debug(f"Skipping manual model: {stored_model_name}")
                        continue
                    else:
                        # manual=False, update last_seen_at
                        cursor.execute("""
                            UPDATE llm_models
                            SET last_seen_at = %s, updated_at = %s, order_number = %s
                            WHERE model_name = %s AND manual = FALSE
                        """, (now, now, idx, stored_model_name))
                        models_updated += 1
                else:
                    # New model, insert
                    cursor.execute("""
                        INSERT INTO llm_models 
                        (model_name, display_name, provider, model_type, version, 
                         order_number, active, deprecated, manual, last_seen_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE, FALSE, FALSE, %s, %s, %s)
                    """, (
                        stored_model_name,  # Store without prefix
                        model_info.get('display_name'),
                        provider,
                        model_info.get('model_type'),
                        model_info.get('version'),
                        idx,
                        now, now, now
                    ))
                    models_added += 1
            
            # Deprecate models not in API response (and manual=false)
            models_deprecated = 0
            for model_name, is_manual in existing_models.items():
                if model_name not in api_model_names and not is_manual:
                    cursor.execute("""
                        UPDATE llm_models
                        SET active = FALSE, deprecated = TRUE, updated_at = %s
                        WHERE model_name = %s AND manual = FALSE
                    """, (now, model_name))
                    models_deprecated += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'provider': provider,
                'models_added': models_added,
                'models_updated': models_updated,
                'models_deprecated': models_deprecated,
                'message': f"Synced {provider}: +{models_added} added, ~{models_updated} updated, -{models_deprecated} deprecated"
            }
            
        except Exception as e:
            logger.error(f"Error syncing models from {provider}: {e}")
            return {
                'success': False,
                'provider': provider,
                'models_added': 0,
                'models_updated': 0,
                'models_deprecated': 0,
                'message': str(e)
            }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def get_forge_model_name(self, model_name: str, provider: str) -> str:
        """
        Generate Forge-compatible model name from provider-native name.
        
        Example:
            model_name='models/gemini-2.0-flash', provider='google'
            → 'Gemini/models/gemini-2.0-flash'
        
        Args:
            model_name: Provider-native model name
            provider: Provider key
        
        Returns:
            Forge-formatted model name
        """
        if provider in SUPPORTED_PROVIDERS:
            prefix = SUPPORTED_PROVIDERS[provider]['forge_prefix']
            return f"{prefix}/{model_name}"
        return model_name
    
    def _strip_forge_prefix(self, model_name: str) -> str:
        """
        Strip Forge prefix from model name to get provider-native name.
        
        Example:
            'Gemini/models/gemini-2.0-flash' → 'models/gemini-2.0-flash'
        
        Args:
            model_name: Possibly Forge-prefixed model name
        
        Returns:
            Provider-native model name
        """
        for provider_config in SUPPORTED_PROVIDERS.values():
            prefix = provider_config['forge_prefix'] + '/'
            if model_name.startswith(prefix):
                return model_name[len(prefix):]
        return model_name
    
    def _row_to_model_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert a database row to a model dictionary."""
        return {
            'id': row[0],
            'model_name': row[1],
            'display_name': row[2],
            'provider': row[3],
            'model_type': row[4],
            'version': row[5],
            'order_number': row[6],
            'active': row[7],
            'deprecated': row[8],
            'manual': row[9],
            'last_seen_at': row[10].isoformat() if row[10] else None,
            'created_at': row[11].isoformat() if row[11] else None,
            'updated_at': row[12].isoformat() if row[12] else None,
        }
    
    def _fetch_models_from_provider(self, provider: str, api_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch models from a specific provider's API.
        
        Args:
            provider: Provider key
            api_key: Optional API key
        
        Returns:
            List of model info dicts, or None on failure
        """
        if provider == 'google':
            return self._fetch_google_models(api_key)
        elif provider == 'groq':
            return self._fetch_groq_models(api_key)
        elif provider == 'anthropic':
            return self._fetch_anthropic_models(api_key)
        elif provider == 'openai':
            return self._fetch_openai_models(api_key)
        else:
            logger.warning(f"No fetch implementation for provider: {provider}")
            return None
    
    def _fetch_google_models(self, api_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch and filter Google Gemini models.
        
        Adapted from llm_lister.py - filters for Gemini 2.x models,
        categorizes by type (flash, flash-lite, pro), and selects best versions.
        """
        import os
        import re
        
        key = api_key or os.getenv('GOOGLE_API_KEY')
        if not key:
            logger.error("No Google API key provided")
            return None
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Google API error: {response.status_code}")
                return None
            
            data = response.json()
            if 'models' not in data:
                logger.error("No 'models' in Google API response")
                return None
            
            model_names = [model['name'] for model in data['models']]
            
            # Filter for Gemini 2.x models
            gemini_models = [name for name in model_names if name.startswith('models/gemini-')]
            
            # Parse models
            parsed = []
            for model in gemini_models:
                parts = model.replace('models/gemini-', '').split('-')
                if len(parts) >= 2:
                    version = parts[0]
                    if not version.startswith('2.'):
                        continue
                    original_mtype = '-'.join(parts[1:])
                    mtype = original_mtype
                    # Map types
                    if mtype.startswith('flash') and 'lite' not in mtype:
                        mtype = 'flash'
                    elif mtype.startswith('flash-lite'):
                        mtype = 'flash-lite'
                    elif mtype.startswith('pro'):
                        mtype = 'pro'
                    parsed.append({
                        'full_name': model, 
                        'version': version, 
                        'type': mtype, 
                        'original_type': original_mtype
                    })
            
            # Group by type
            groups = {}
            for p in parsed:
                t = p['type']
                if t not in groups:
                    groups[t] = []
                groups[t].append(p)
            
            # For each type, select 2.0 and 2.5 if available
            selected = {}
            for t, models in groups.items():
                models_2_0 = [m for m in models if m['version'] == '2.0']
                models_2_5 = [m for m in models if m['version'] == '2.5']
                if models_2_0:
                    # Sort: prefer non-exp, shorter names
                    models_2_0.sort(key=lambda x: ('exp' in x['original_type'], len(x['original_type'])))
                    selected[(t, '2.0')] = models_2_0[0]['full_name']
                if models_2_5:
                    models_2_5.sort(key=lambda x: ('exp' in x['original_type'], len(x['original_type'])))
                    selected[(t, '2.5')] = models_2_5[0]['full_name']
            
            # Define order: flash, flash-lite, pro
            order = ['flash', 'flash-lite', 'pro']
            
            # Get selected models in order: for each type, 2.5 then 2.0
            result = []
            for t in order:
                if (t, '2.5') in selected:
                    result.append({
                        'model_name': selected[(t, '2.5')],
                        'display_name': f"Gemini 2.5 {t.replace('-', ' ').title()}",
                        'model_type': t,
                        'version': '2.5'
                    })
                if (t, '2.0') in selected:
                    result.append({
                        'model_name': selected[(t, '2.0')],
                        'display_name': f"Gemini 2.0 {t.replace('-', ' ').title()}",
                        'model_type': t,
                        'version': '2.0'
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Google models: {e}")
            return None
    
    def _fetch_groq_models(self, api_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch Groq models.
        Placeholder implementation - extend when needed.
        """
        import os
        
        key = api_key or os.getenv('GROQ_API_KEY')
        if not key:
            logger.warning("No Groq API key provided")
            return None
        
        try:
            response = requests.get(
                'https://api.groq.com/openai/v1/models',
                headers={'Authorization': f'Bearer {key}'},
                timeout=30
            )
            if response.status_code != 200:
                logger.error(f"Groq API error: {response.status_code}")
                return None
            
            data = response.json()
            models = data.get('data', [])
            
            result = []
            for idx, model in enumerate(models):
                model_id = model.get('id', '')
                result.append({
                    'model_name': model_id,
                    'display_name': model_id.replace('-', ' ').title(),
                    'model_type': 'llama' if 'llama' in model_id.lower() else 'other',
                    'version': None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Groq models: {e}")
            return None
    
    def _fetch_anthropic_models(self, api_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch Anthropic Claude models.
        Placeholder implementation - extend when needed.
        """
        import os
        
        key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not key:
            logger.warning("No Anthropic API key provided")
            return None
        
        # Anthropic doesn't have a public models list API, so return known models
        return [
            {'model_name': 'claude-3-5-sonnet-20241022', 'display_name': 'Claude 3.5 Sonnet', 'model_type': 'sonnet', 'version': '3.5'},
            {'model_name': 'claude-3-5-haiku-20241022', 'display_name': 'Claude 3.5 Haiku', 'model_type': 'haiku', 'version': '3.5'},
            {'model_name': 'claude-3-opus-20240229', 'display_name': 'Claude 3 Opus', 'model_type': 'opus', 'version': '3'},
        ]
    
    def _fetch_openai_models(self, api_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch OpenAI models.
        Placeholder implementation - extend when needed.
        """
        import os
        
        key = api_key or os.getenv('OPENAI_API_KEY')
        if not key:
            logger.warning("No OpenAI API key provided")
            return None
        
        try:
            response = requests.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {key}'},
                timeout=30
            )
            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.status_code}")
                return None
            
            data = response.json()
            models = data.get('data', [])
            
            # Filter for chat models only
            chat_models = [m for m in models if m.get('id', '').startswith(('gpt-4', 'gpt-3.5'))]
            
            result = []
            for model in chat_models:
                model_id = model.get('id', '')
                result.append({
                    'model_name': model_id,
                    'display_name': model_id.upper().replace('-', ' '),
                    'model_type': 'gpt-4' if 'gpt-4' in model_id else 'gpt-3.5',
                    'version': None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching OpenAI models: {e}")
            return None


# Global instance
llm_service = LLMService()
