"""Service for generating A2UI-based help visualizations."""

import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class A2UIHelpService:
    """Service for generating A2UI declarative UI components for math help."""
    
    # A2UI Catalog ID - version this when making breaking changes
    CATALOG_ID = "https://smartboy.ai/a2ui_catalogs/math-v0.1"
    
    # Component vocabulary for Grade 6-8 math
    COMPONENT_CATALOG = {
        "MoveAcrossEquals": {
            "description": "Algebra transposition - circle term, show arrow moving across equals",
            "use_cases": ["solving equations", "variable isolation", "algebra"]
        },
        "NumberLineJump": {
            "description": "Number line with jumps and arcs",
            "use_cases": ["addition", "subtraction", "integers", "distance", "inequalities"]
        },
        "BarModel": {
            "description": "Segmented bar model for part-whole relationships",
            "use_cases": ["fractions", "ratios", "percent", "part-whole", "unitary method"]
        },
        "FractionSimplify": {
            "description": "Fraction simplification with strike-through cancellation",
            "use_cases": ["simplifying fractions", "GCD", "cancellation"]
        },
        "RatioTable": {
            "description": "Ratio/proportion table with highlighting",
            "use_cases": ["ratios", "proportions", "scaling", "equivalent ratios"]
        },
        # Narrative/layout primitives
        "ExplainCard": {
            "description": "Container with title and learning objective",
            "use_cases": ["structure", "organization"]
        },
        "StepList": {
            "description": "Ordered list of steps",
            "use_cases": ["step-by-step explanations"]
        },
        "MathText": {
            "description": "Rich math text (supports LaTeX)",
            "use_cases": ["equations", "expressions"]
        }
    }
    
    def __init__(self):
        """Initialize the A2UI help service."""
        pass
    
    def get_a2ui_prompt_instructions(
        self,
        subject_name: str,
        complexity: Optional[str] = None
    ) -> str:
        """
        Generate A2UI-specific prompt instructions for the AI model.
        
        Args:
            subject_name: Subject name for context
            complexity: Question complexity (simple/moderate/complex)
            
        Returns:
            Formatted prompt instructions for A2UI generation
        """
        
        return f"""
**A2UI Visual Mode - ENABLED**

You MUST generate declarative A2UI components for visual explanations.

**Available Components (from catalog {self.CATALOG_ID}):**

1. **MoveAcrossEquals** - Show equation transposition with circled term + curved arrow
   - Use for: Solving equations, moving terms across =, sign changes
   - Props: initial (equation with tokens), final (equation after move), move (which token), emphasis (circle/box), annotation (arrow)

2. **NumberLineJump** - Number line with labeled jumps
   - Use for: Addition/subtraction, integers, distance, inequalities
   - Props: min, max, start, jumps (array of {{delta, label?}}), tickStep?, showLabels?

3. **BarModel** - Segmented bar for part-whole relationships
   - Use for: Fractions, ratios, percent, part-whole problems
   - Props: totalLabel?, segments (array of {{label?, value?, shaded?}}), unknownIndex?

4. **FractionSimplify** - Fraction with strike-through cancellation
   - Use for: Simplifying fractions, showing GCD cancellation
   - Props: numerator, denominator, steps (array of {{cancel?, result?, note?}})

5. **RatioTable** - Table with highlighted cells
   - Use for: Ratios, proportions, scaling
   - Props: columns (array), rows (2D array), highlight (array of {{row, col}}), caption?

6. **ExplainCard**, **StepList**, **MathText** - Layout/narrative primitives

**A2UI Message Format (JSONL):**

You MUST return A2UI messages as an array of JSON objects. Each help step should generate:

1. **surfaceUpdate** message with component instances
2. **beginRendering** message at the end

**Example for "Solve -4x + 7 = 15":**

```json
[
  {{
    "surfaceUpdate": {{
      "surfaceId": "help",
      "components": [
        {{
          "id": "root",
          "component": {{
            "MoveAcrossEquals": {{
              "initial": {{
                "left": [
                  {{"id": "t1", "text": "-4x"}},
                  {{"id": "t2", "text": "+"}},
                  {{"id": "t3", "text": "7"}}
                ],
                "right": [{{"id": "t4", "text": "15"}}]
              }},
              "final": {{
                "left": [{{"id": "t1b", "text": "-4x"}}],
                "right": [
                  {{"id": "t4b", "text": "15"}},
                  {{"id": "t2b", "text": "-"}},
                  {{"id": "t3b", "text": "7"}}
                ]
              }},
              "move": {{
                "tokenId": "t3",
                "toSide": "right",
                "operatorChange": "+->"
              }},
              "emphasis": {{
                "shape": "circle",
                "tokenId": "t3"
              }},
              "annotation": {{
                "arrow": {{
                  "fromTokenId": "t3",
                  "toTokenId": "t3b",
                  "style": "curve"
                }}
              }}
            }}
          }}
        }}
      ]
    }}
  }},
  {{
    "beginRendering": {{
      "surfaceId": "help",
      "catalogId": "{self.CATALOG_ID}",
      "root": "root"
    }}
  }}
]
```

**Critical Rules:**

1. **Tokenization**: For equations, give each token a unique `id` (e.g., t1, t2, t3)
2. **Component IDs**: Every component instance needs a unique `id`
3. **No limits**: Generate as many A2UI components as needed for clarity (no max limit)
4. **One component per step**: Typically 1 visual component per help step
5. **End with beginRendering**: Always end the array with beginRendering message
6. **Match the question type**: Choose the right component for the concept
7. **Prefer A2UI over text**: Use visual components whenever they aid understanding

**Component Selection Guide:**

- Algebra equations → **MoveAcrossEquals**
- Addition/subtraction/integers → **NumberLineJump**
- Fractions/ratios/percent → **BarModel** or **FractionSimplify**
- Proportions/scaling → **RatioTable**
- Multi-step → Combine multiple components in sequence

**Integration with help_steps:**

Each step in your help_steps response should include a "visual" object with "type": "a2ui" and the "a2ui_messages" field containing the A2UI message array for that specific step.

Return format:
```json
{{
  "help_steps": [
    {{
      "step_number": 1,
      "explanation": "**Step 1: Move +7 across the equals**\\n\\nWhen we move a term...",
      "visual": {{
        "type": "a2ui",
        "a2ui_messages": [ /* array of surfaceUpdate + beginRendering */ ]
      }}
    }}
  ]
}}
```

CRITICAL: You MUST nest a2ui_messages inside a visual object with type "a2ui". Do NOT put a2ui_messages directly in the step object.

Generate rich, educational A2UI visualizations for {subject_name} concepts.
"""
    
    def validate_a2ui_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate A2UI message array structure.
        
        Args:
            messages: Array of A2UI messages to validate
            
        Returns:
            Dict with:
                - valid: bool
                - error: str (if invalid)
                - component_count: int
                - message_types: List[str]
        """
        try:
            if not isinstance(messages, list):
                return {
                    "valid": False,
                    "error": "Messages must be an array",
                    "component_count": 0,
                    "message_types": []
                }
            
            message_types = []
            component_count = 0
            has_begin_rendering = False
            
            for idx, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    return {
                        "valid": False,
                        "error": f"Message {idx} is not an object",
                        "component_count": component_count,
                        "message_types": message_types
                    }
                
                # Check for valid message types
                if "surfaceUpdate" in msg:
                    message_types.append("surfaceUpdate")
                    
                    # Count components
                    components = msg.get("surfaceUpdate", {}).get("components", [])
                    component_count += len(components)
                    
                    # Validate component structure
                    for comp_idx, comp in enumerate(components):
                        if "id" not in comp or "component" not in comp:
                            return {
                                "valid": False,
                                "error": f"Component {comp_idx} missing 'id' or 'component' field",
                                "component_count": component_count,
                                "message_types": message_types
                            }
                        
                        # Check component has exactly one type key
                        comp_obj = comp.get("component", {})
                        if not isinstance(comp_obj, dict) or len(comp_obj) != 1:
                            return {
                                "valid": False,
                                "error": f"Component {comp_idx} must have exactly one type key",
                                "component_count": component_count,
                                "message_types": message_types
                            }
                
                elif "beginRendering" in msg:
                    message_types.append("beginRendering")
                    has_begin_rendering = True
                    
                    # Validate required fields
                    begin_msg = msg.get("beginRendering", {})
                    if "root" not in begin_msg:
                        return {
                            "valid": False,
                            "error": "beginRendering missing 'root' field",
                            "component_count": component_count,
                            "message_types": message_types
                        }
                
                elif "dataModelUpdate" in msg:
                    message_types.append("dataModelUpdate")
                
                else:
                    return {
                        "valid": False,
                        "error": f"Unknown message type at index {idx}",
                        "component_count": component_count,
                        "message_types": message_types
                    }
            
            # Should have at least one beginRendering
            if not has_begin_rendering:
                return {
                    "valid": False,
                    "error": "Missing beginRendering message",
                    "component_count": component_count,
                    "message_types": message_types
                }
            
            return {
                "valid": True,
                "error": None,
                "component_count": component_count,
                "message_types": message_types
            }
            
        except Exception as e:
            logger.error(f"Error validating A2UI messages: {e}")
            return {
                "valid": False,
                "error": f"Validation exception: {str(e)}",
                "component_count": 0,
                "message_types": []
            }
    
    def extract_a2ui_from_response(
        self,
        response_text: str,
        step_number: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extract and validate A2UI messages from AI response.
        
        Args:
            response_text: Raw AI response text
            step_number: Step number for logging
            
        Returns:
            Validated A2UI messages array, or None if invalid
        """
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            
            # Check if it's wrapped in help_steps structure
            if "help_steps" in data and isinstance(data["help_steps"], list):
                # Find the step
                for step in data["help_steps"]:
                    if step.get("step_number") == step_number:
                        # Check for a2ui_messages inside visual object (correct structure)
                        if "visual" in step and isinstance(step["visual"], dict):
                            if step["visual"].get("type") == "a2ui" and "a2ui_messages" in step["visual"]:
                                messages = step["visual"]["a2ui_messages"]
                                
                                # Validate
                                validation = self.validate_a2ui_messages(messages)
                                
                                if validation["valid"]:
                                    logger.info(
                                        f"Extracted valid A2UI messages from visual object: {validation['component_count']} components, "
                                        f"types={validation['message_types']}"
                                    )
                                    return messages
                                else:
                                    logger.warning(f"Invalid A2UI messages in visual object: {validation['error']}")
                                    return None
                        
                        # Fallback: Check for legacy a2ui_messages directly in step (for backwards compatibility)
                        elif "a2ui_messages" in step:
                            logger.warning(f"Found a2ui_messages directly in step (legacy format) - should be in visual object")
                            messages = step["a2ui_messages"]
                            
                            # Validate
                            validation = self.validate_a2ui_messages(messages)
                            
                            if validation["valid"]:
                                logger.info(
                                    f"Extracted valid A2UI messages (legacy format): {validation['component_count']} components, "
                                    f"types={validation['message_types']}"
                                )
                                return messages
                            else:
                                logger.warning(f"Invalid A2UI messages (legacy format): {validation['error']}")
                                return None
            
            # Try direct array format
            elif isinstance(data, list):
                validation = self.validate_a2ui_messages(data)
                
                if validation["valid"]:
                    logger.info(
                        f"Extracted valid A2UI messages: {validation['component_count']} components, "
                        f"types={validation['message_types']}"
                    )
                    return data
                else:
                    logger.warning(f"Invalid A2UI messages: {validation['error']}")
                    return None
            
            logger.warning("Response does not contain A2UI messages in expected format")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse A2UI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting A2UI messages: {e}")
            return None


# Singleton instance
a2ui_help_service = A2UIHelpService()
