"""
Unit tests for GradeToneConfig loader
"""

import pytest
from app.utils.grade_tone_loader import GradeToneConfig


class TestGradeToneConfig:
    """Test grade tone configuration loading and retrieval"""
    
    def test_load_config(self):
        """Test that config loads successfully"""
        config = GradeToneConfig.load()
        assert config is not None
        assert isinstance(config, dict)
        assert 'default' in config
        
    def test_get_tone_for_valid_grades(self):
        """Test getting tone config for valid grades 1-12"""
        for grade in range(1, 13):
            tone_config = GradeToneConfig.get_tone_for_grade(grade)
            assert tone_config is not None
            assert 'target_audience' in tone_config
            assert 'language_level' in tone_config
            assert 'sentence_structure' in tone_config
            assert 'explanation_approach' in tone_config
            assert 'example_style' in tone_config
            assert 'tone_instruction' in tone_config
    
    def test_get_tone_for_none_grade(self):
        """Test that None grade returns default (Grade 6)"""
        tone_config = GradeToneConfig.get_tone_for_grade(None)
        default_config = GradeToneConfig.load().get('default')
        assert tone_config == default_config
        assert 'Grade 6' in tone_config['target_audience']
    
    def test_get_tone_for_invalid_grade(self):
        """Test that invalid grades return default"""
        for invalid_grade in [0, 13, 99, -1]:
            tone_config = GradeToneConfig.get_tone_for_grade(invalid_grade)
            default_config = GradeToneConfig.load().get('default')
            assert tone_config == default_config
    
    def test_get_prompt_instruction(self):
        """Test getting just the prompt instruction text"""
        instruction = GradeToneConfig.get_prompt_instruction(6)
        assert isinstance(instruction, str)
        assert len(instruction) > 0
        assert 'explain' in instruction.lower() or 'teaching' in instruction.lower()
    
    def test_grade_1_vs_grade_12_different_tones(self):
        """Test that Grade 1 and Grade 12 have significantly different tones"""
        grade1 = GradeToneConfig.get_tone_for_grade(1)
        grade12 = GradeToneConfig.get_tone_for_grade(12)
        
        # Grade 1 should mention younger age/simpler language
        assert '6-7' in grade1['target_audience'] or 'Grade 1' in grade1['target_audience']
        
        # Grade 12 should mention high school senior
        assert 'Grade 12' in grade12['target_audience'] and 'senior' in grade12['target_audience'].lower()
        
        # Instructions should be different
        assert grade1['tone_instruction'] != grade12['tone_instruction']
    
    def test_default_is_grade_6(self):
        """Test that default config matches Grade 6"""
        default_config = GradeToneConfig.load().get('default')
        grade6_config = GradeToneConfig.load().get('6')
        
        # Default should be Grade 6
        assert 'Grade 6' in default_config['target_audience']
        assert '11-12' in default_config['target_audience']
    
    def test_reload_config(self):
        """Test that reload clears cache"""
        # Load config
        config1 = GradeToneConfig.load()
        
        # Reload
        GradeToneConfig.reload()
        
        # Load again
        config2 = GradeToneConfig.load()
        
        # Should have same content
        assert config1 == config2
