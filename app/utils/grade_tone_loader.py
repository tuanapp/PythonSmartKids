"""
Grade Tone Configuration Loader

Provides grade-specific tone and language level configurations for AI-generated help.
Uses a JSON configuration file to define appropriate explanatory tone for each grade level.
"""

import json
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GradeToneConfig:
    """
    Singleton class to load and provide grade-specific tone configurations.
    
    Loads configuration from grade_tone_config.json and caches it for performance.
    Provides fallback to default (Grade 6) configuration when specific grade not found.
    """
    
    _config: Optional[Dict] = None
    _config_path: Path = Path(__file__).parent.parent / 'config' / 'grade_tone_config.json'
    
    @classmethod
    def load(cls) -> Dict:
        """
        Load the grade tone configuration from JSON file.
        Uses caching to avoid repeated file reads.
        
        Returns:
            dict: Complete configuration dictionary with all grade levels
            
        Raises:
            FileNotFoundError: If grade_tone_config.json is missing
            json.JSONDecodeError: If JSON file is malformed
        """
        if cls._config is None:
            try:
                with open(cls._config_path, 'r', encoding='utf-8') as f:
                    cls._config = json.load(f)
                logger.info(f"Loaded grade tone configuration from {cls._config_path}")
            except FileNotFoundError:
                logger.error(f"Grade tone config file not found: {cls._config_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in grade tone config: {e}")
                raise
                
        return cls._config
    
    @classmethod
    def get_tone_for_grade(cls, grade_level: Optional[int]) -> Dict:
        """
        Get tone configuration for a specific grade level.
        
        Args:
            grade_level: Student's grade level (1-12), or None
            
        Returns:
            dict: Tone configuration with keys:
                - target_audience: Description of target student
                - language_level: Vocabulary and complexity guidelines
                - sentence_structure: Sentence construction guidelines
                - explanation_approach: How to approach explanations
                - example_style: How to structure examples
                - tone_instruction: Direct instruction for AI prompt
                
        Notes:
            - Returns default (Grade 6) config if grade_level is None
            - Returns default (Grade 6) config if grade not in 1-12 range
            - Logs warnings when falling back to default
        """
        config = cls.load()
        
        # Handle missing or invalid grade level
        if grade_level is None:
            logger.warning("Grade level not provided, using default (Grade 6) tone")
            return config.get('default')
        
        # Convert to string for JSON key lookup
        grade_key = str(grade_level)
        
        # Check if grade exists in config
        if grade_key in config:
            logger.debug(f"Using tone configuration for Grade {grade_level}")
            return config[grade_key]
        else:
            logger.warning(
                f"Grade {grade_level} not found in config, using default (Grade 6) tone"
            )
            return config.get('default')
    
    @classmethod
    def get_prompt_instruction(cls, grade_level: Optional[int]) -> str:
        """
        Get the direct prompt instruction text for a specific grade level.
        This is the text that will be inserted into the AI prompt.
        
        Args:
            grade_level: Student's grade level (1-12), or None
            
        Returns:
            str: The tone_instruction text ready to insert into prompt
            
        Example:
            >>> GradeToneConfig.get_prompt_instruction(6)
            "Explain like you're teaching an 11-year-old middle schooler..."
        """
        tone_config = cls.get_tone_for_grade(grade_level)
        return tone_config.get('tone_instruction', '')
    
    @classmethod
    def reload(cls):
        """
        Force reload of configuration from file.
        Useful for testing or when config file is updated at runtime.
        """
        cls._config = None
        logger.info("Grade tone configuration cache cleared, will reload on next access")
