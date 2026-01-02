-- Migration: Add visual limits to subjects table
-- Date: 2026-01-02
-- Description: Add visual_json_max and visual_svg_max columns to control per-subject visual generation

-- Add visual_json_max column (JSON-based visual rendering max per subject)
DO $$ 
BEGIN
    BEGIN
        ALTER TABLE subjects ADD COLUMN visual_json_max INTEGER DEFAULT 0 NOT NULL;
    EXCEPTION
        WHEN duplicate_column THEN NULL;
    END;
END $$;

-- Add visual_svg_max column (AI-generated SVG max per subject)
DO $$ 
BEGIN
    BEGIN
        ALTER TABLE subjects ADD COLUMN visual_svg_max INTEGER DEFAULT 0 NOT NULL;
    EXCEPTION
        WHEN duplicate_column THEN NULL;
    END;
END $$;

-- Update Math/Maths subjects with default visual limits
-- Math should support JSON visuals (shapes) and experimental AI-SVG diagrams
UPDATE subjects 
SET visual_json_max = 3, visual_svg_max = 1 
WHERE LOWER(name) IN ('math', 'maths', 'mathematics')
  AND (visual_json_max = 0 OR visual_svg_max = 0);

-- Create index for subjects with visual capabilities enabled
CREATE INDEX IF NOT EXISTS idx_subjects_visual_enabled 
ON subjects(visual_json_max, visual_svg_max) 
WHERE visual_json_max > 0 OR visual_svg_max > 0;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration: add_visual_limits_to_subjects completed successfully';
END $$;
