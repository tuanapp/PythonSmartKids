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
            "description": "Algebra transposition - circle term, show arrow moving across equals (ADDITION/SUBTRACTION ONLY)",
            "use_cases": ["moving terms across equals", "addition in equations", "subtraction in equations", "sign changes", "variable isolation by add/subtract"]
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
        "RectanglePerimeter": {
            "description": "Rectangle with labeled dimensions showing perimeter calculation",
            "use_cases": ["perimeter", "rectangle perimeter", "perimeter of rectangle", "distance around"]
        },
        "RectangleArea": {
            "description": "Rectangle with grid overlay showing area calculation",
            "use_cases": ["area", "rectangle area", "area of rectangle", "unit squares", "square units"]
        },
        "DivideBothSides": {
            "description": "Division operation applied to both sides of equation (shows intermediate step)",
            "use_cases": ["division", "solving equations with coefficients", "isolate variable by division", "divide both sides"]
        },
        "MultiplyBothSides": {
            "description": "Multiplication operation applied to both sides of equation (shows intermediate step)",
            "use_cases": ["multiplication", "solving fractions", "isolate variable by multiplication", "multiply both sides"]
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
   - Use for: Moving terms across = (ADDITION/SUBTRACTION ONLY), sign changes (+ becomes -, - becomes +)
   - NOT for division/multiplication - use DivideBothSides or MultiplyBothSides instead
   - Props: initial (equation with tokens), final (equation after move), move (which token), emphasis (circle/box), annotation (arrow)
   - CRITICAL: "left" and "right" arrays represent the two sides of the equation. DO NOT include "=" in either array. The equals sign is automatically rendered between them.
   - Example structure: {{{{"left": [{{{{"id": "t1", "text": "2x"}}}}], "right": [{{{{"id": "t2", "text": "10"}}}}]}}}} renders as "2x = 10"

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

6. **RectanglePerimeter** - Rectangle with labeled dimensions showing perimeter
   - Use for: Perimeter of rectangle questions, distance around shapes
   - Props: length (number), width (number), showFormula? (boolean, default true), unit? (string, default "cm")
   - Example: {{"RectanglePerimeter": {{"length": 8, "width": 5, "showFormula": true, "unit": "cm"}}}}

7. **RectangleArea** - Rectangle with grid overlay showing area
   - Use for: Area of rectangle questions, square units, counting squares
   - Props: length (number), width (number), showFormula? (boolean, default true), showGrid? (boolean, default true), unit? (string, default "cm")
   - Example: {{"RectangleArea": {{"length": 8, "width": 5, "showFormula": true, "showGrid": true, "unit": "cm"}}}}

8. **DivideBothSides** - Division operation on both sides of equation
   - Use for: Solving equations like 2x = 12 (divide both sides by 2)
   - Props: left (tokens array), right (tokens array), divisor (number), resultLeft (tokens array), resultRight (tokens array), annotation? (string)
   - Shows: Original equation → Division symbols on both sides → Simplified result
   - Example: {{{{"DivideBothSides": {{{{"left": [{{{{"id": "t1", "text": "2x"}}}}], "right": [{{{{"id": "t2", "text": "12"}}}}], "divisor": 2, "resultLeft": [{{{{"id": "t3", "text": "x"}}}}], "resultRight": [{{{{"id": "t4", "text": "6"}}}}], "annotation": "Divide both sides by 2 to isolate x"}}}}}}}}

9. **MultiplyBothSides** - Multiplication operation on both sides of equation
   - Use for: Solving equations like x/2 = 5 (multiply both sides by 2)
   - Props: left (tokens array), right (tokens array), multiplier (number), resultLeft (tokens array), resultRight (tokens array), annotation? (string)
   - Shows: Original equation → Multiplication symbols on both sides → Simplified result
   - Example: {{{{"MultiplyBothSides": {{{{"left": [{{{{"id": "t1", "text": "x/2"}}}}], "right": [{{{{"id": "t2", "text": "5"}}}}], "multiplier": 2, "resultLeft": [{{{{"id": "t3", "text": "x"}}}}], "resultRight": [{{{{"id": "t4", "text": "10"}}}}], "annotation": "Multiply both sides by 2 to isolate x"}}}}}}}}

10. **ExplainCard**, **StepList**, **MathText** - Layout/narrative primitives

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
                  {{{{"id": "t1", "text": "-4x"}}}},
                  {{{{"id": "t2", "text": "+"}}}},
                  {{{{"id": "t3", "text": "7"}}}}
                ],
                "right": [{{{{"id": "t4", "text": "15"}}}}]
              }},
              "final": {{
                "left": [{{{{"id": "t1b", "text": "-4x"}}}}],
                "right": [
                  {{{{"id": "t4b", "text": "15"}}}},
                  {{{{"id": "t2b", "text": "-"}}}},
                  {{{{"id": "t3b", "text": "7"}}}}
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

**Example for "What is the perimeter of a rectangle with length 8 cm and width 5 cm?":**

```json
[
  {{
    "surfaceUpdate": {{
      "surfaceId": "help",
      "components": [
        {{
          "id": "perimeter-viz",
          "component": {{
            "RectanglePerimeter": {{
              "length": 8,
              "width": 5,
              "showFormula": true,
              "unit": "cm"
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
      "root": "perimeter-viz"
    }}
  }}
]
```

**Example for "What is the area of a rectangle with length 8 cm and width 5 cm?":**

```json
[
  {{
    "surfaceUpdate": {{
      "surfaceId": "help",
      "components": [
        {{
          "id": "area-viz",
          "component": {{
            "RectangleArea": {{
              "length": 8,
              "width": 5,
              "showFormula": true,
              "showGrid": true,
              "unit": "cm"
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
      "root": "area-viz"
    }}
  }}
]
```

**Example for "Solve 2y = 12" (division):**

```json
[
  {{
    "surfaceUpdate": {{
      "surfaceId": "help",
      "components": [
        {{
          "id": "divide-viz",
          "component": {{
            "MoveAcrossEquals": {{
              "initial": {{
                "left": [
                  {{{{"id": "t1", "text": "2"}}}},
                  {{{{"id": "t2", "text": "y"}}}}
                ],
                "right": [{{{{"id": "t3", "text": "12"}}}}]
              }},
              "final": {{
                "left": [{{{{"id": "t2b", "text": "y"}}}}],
                "right": [{{{{"id": "t3b", "text": "6"}}}}]
              }},
              "move": {{
                "tokenId": "t1",
                "toSide": "right",
                "operatorChange": "*->/"
              }},
              "emphasis": {{
                "shape": "circle",
                "tokenId": "t1"
              }},
              "annotation": {{
                "arrow": {{
                  "fromTokenId": "t1",
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
      "root": "divide-viz"
    }}
  }}
]
```

**Example for "Solve 3y = 24" (using DivideBothSides):**

```json
[
  {{
    "surfaceUpdate": {{
      "surfaceId": "help",
      "components": [
        {{
          "id": "divide-step",
          "component": {{
            "DivideBothSides": {{
              "left": [
                {{{{"id": "t1", "text": "3"}}}},
                {{{{"id": "t2", "text": "y"}}}}
              ],
              "right": [{{{{"id": "t3", "text": "24"}}}}],
              "divisor": 3,
              "resultLeft": [{{{{"id": "t4", "text": "y"}}}}],
              "resultRight": [{{{{"id": "t5", "text": "8"}}}}],
              "annotation": "Divide both sides by 3 to isolate y"
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
      "root": "divide-step"
    }}
  }}
]
```

**Example for "Solve x/2 = 7" (using MultiplyBothSides):**

```json
[
  {{
    "surfaceUpdate": {{
      "surfaceId": "help",
      "components": [
        {{
          "id": "multiply-step",
          "component": {{
            "MultiplyBothSides": {{
              "left": [
                {{{{"id": "t1", "text": "x"}}}},
                {{{{"id": "t2", "text": "/"}}}},
                {{{{"id": "t3", "text": "2"}}}}
              ],
              "right": [{{{{"id": "t4", "text": "7"}}}}],
              "multiplier": 2,
              "resultLeft": [{{{{"id": "t5", "text": "x"}}}}],
              "resultRight": [{{{{"id": "t6", "text": "14"}}}}],
              "annotation": "Multiply both sides by 2 to isolate x"
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
      "root": "multiply-step"
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

- **Addition/Subtraction in equations** (moving terms across =) → **MoveAcrossEquals**
- **Division in equations** (coefficient like 2x = 12) → **DivideBothSides**
- **Multiplication in equations** (fraction like x/2 = 5) → **MultiplyBothSides**
- **Multi-step equations** → Combine components (e.g., MoveAcrossEquals first, then DivideBothSides)
- Addition/subtraction/integers → **NumberLineJump**
- Fractions/ratios/percent → **BarModel** or **FractionSimplify**
- Proportions/scaling → **RatioTable**
- Rectangle perimeter → **RectanglePerimeter** (PREFERRED for perimeter questions)
- Rectangle area → **RectangleArea** (PREFERRED for area questions)
- Multi-step → Combine multiple components in sequence

**CRITICAL: Choose the right component for the operation:**
- Use **MoveAcrossEquals** ONLY for adding/subtracting terms across equals (sign changes)
- Use **DivideBothSides** for division operations (both sides divided by same number)
- Use **MultiplyBothSides** for multiplication operations (both sides multiplied by same number)
- For "2x + 5 = 15": Step 1 uses MoveAcrossEquals (+5 → -5), Step 2 uses DivideBothSides (÷2)

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
    
    def extract_component_names(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract component names from A2UI messages.
        
        Args:
            messages: Array of A2UI messages
            
        Returns:
            List of component names (e.g., ["MoveAcrossEquals", "DivideBothSides"])
        """
        component_names = []
        
        try:
            for msg in messages:
                if "surfaceUpdate" in msg:
                    components = msg.get("surfaceUpdate", {}).get("components", [])
                    
                    for comp in components:
                        comp_obj = comp.get("component", {})
                        
                        # Extract the component type (should be a single key)
                        if isinstance(comp_obj, dict) and len(comp_obj) > 0:
                            # Get the first (and should be only) key
                            component_type = list(comp_obj.keys())[0]
                            component_names.append(component_type)
            
            return component_names
            
        except Exception as e:
            logger.error(f"Error extracting component names: {e}")
            return []


# Singleton instance
a2ui_help_service = A2UIHelpService()
