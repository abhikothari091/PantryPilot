# 6 Synthetic Data Generation Scenarios

This document describes the 6 scenarios used to generate 12,000 synthetic recipes using **Groq API (Llama 3.1 8B)**.

## Overview

The scenarios were designed to cover diverse real-world use cases for recipe generation, ensuring the fine-tuned model can handle various inventory situations, dietary preferences, and cultural cuisines.

### Total Dataset Distribution
- **Total recipes**: 12,000
- **Scenario 1**: 3,000 (25%)
- **Scenario 2**: 2,400 (20%)
- **Scenario 3**: 1,800 (15%)
- **Scenario 4**: 1,200 (10%)
- **Scenario 5**: 2,400 (20%)
- **Scenario 6**: 1,200 (10%)

---

## Scenario 1: Full Inventory Usage (3,000 recipes)
**Purpose**: Generate recipes using all available ingredients without additional constraints.

### Subtypes:
1. **Cultural-specific** (2,100 recipes)
   - Uses cuisine-specific ingredients (e.g., Italian: pasta, tomatoes, basil)
   - Tests model's understanding of cultural cuisine patterns

2. **Neutral** (600 recipes)
   - Uses common everyday ingredients
   - Tests basic recipe generation without cultural context

3. **Fusion** (300 recipes)
   - Combines ingredients from 2 different cuisines
   - Tests model's creativity in cross-cultural recipes

**Example Input**:
```json
{
  "inventory": ["pasta", "tomatoes", "garlic", "olive oil", "basil"],
  "scenario": "scenario_1",
  "subtype": "cultural_specific"
}
```

---

## Scenario 2: Inventory + Dietary Preference (2,400 recipes)
**Purpose**: Generate recipes that respect dietary constraints (vegan, vegetarian, gluten-free, dairy-free).

### Distribution by Preference:
- **Vegan**: 800 recipes
- **Vegetarian**: 800 recipes
- **Gluten-free**: 400 recipes
- **Dairy-free**: 400 recipes

**Why these preferences**:
- **Vegan/Vegetarian**: Most restrictive dietary constraints requiring careful ingredient selection
- **Gluten-free**: Common allergy requiring ingredient substitution
- **Dairy-free**: Lactose intolerance and allergy considerations

**Example Input**:
```json
{
  "inventory": ["tofu", "soy sauce", "rice", "vegetables", "sesame oil"],
  "preference": "vegan",
  "scenario": "scenario_2"
}
```

---

## Scenario 3: Inventory + Cuisine (1,800 recipes)
**Purpose**: Generate recipes in specific cultural cuisine styles.

### Supported Cuisines:
- Italian (300)
- Chinese (300)
- Mexican (300)
- Indian (300)
- Japanese (300)
- Korean (300)

**Why these cuisines**:
- Global popularity and diversity
- Distinct ingredient patterns and cooking techniques
- Tests model's cultural knowledge

**Example Input**:
```json
{
  "inventory": ["chicken", "onions", "tomatoes", "cumin", "cilantro"],
  "cuisine": "Mexican",
  "scenario": "scenario_3"
}
```

---

## Scenario 4: All Specified (Cuisine + Preference) (1,200 recipes)
**Purpose**: Generate recipes with BOTH cuisine style AND dietary preference constraints.

**Complexity**: Highest constraint combination
- Must respect cultural authenticity
- Must adhere to dietary restrictions
- Tests model's ability to handle multiple constraints

**Example Input**:
```json
{
  "inventory": ["rice flour", "coconut milk", "vegetables", "tofu"],
  "preference": "vegan",
  "cuisine": "Thai",
  "scenario": "scenario_4"
}
```

---

## Scenario 5: Specific Ingredients - All Available (2,400 recipes)
**Purpose**: User requests specific ingredients that are all available in inventory.

### Features:
- User explicitly requests 2-4 ingredients
- All requested ingredients are in inventory
- 30% chance of additional preference/cuisine constraints

**Why this scenario**:
- Mimics real user behavior ("I want to use these ingredients")
- Tests prioritization of requested ingredients
- Ensures requested ingredients appear in final recipe

**Example Input**:
```json
{
  "inventory": ["chicken", "rice", "broccoli", "soy sauce", "garlic", "ginger"],
  "requested_ingredients": ["chicken", "broccoli", "soy sauce"],
  "preference": "None",
  "cuisine": "Chinese",
  "scenario": "scenario_5"
}
```

---

## Scenario 6: Specific Ingredients - Some/All Missing (1,200 recipes)
**Purpose**: Handle cases where requested ingredients are NOT in inventory.

### Subtypes:
1. **Partial match** (900 recipes)
   - Some requested ingredients available
   - Some missing
   - Model should suggest alternatives or substitutions

2. **No match** (300 recipes)
   - ALL requested ingredients missing
   - Model should suggest completely alternative recipe
   - Tests fallback behavior

**Why this scenario**:
- Real-world UX: Users often request unavailable ingredients
- Tests model's ability to suggest alternatives
- Prevents hallucination of unavailable ingredients

**Example Input (Partial)**:
```json
{
  "inventory": ["flour", "eggs", "milk"],
  "requested_ingredients": ["chocolate", "butter", "flour"],
  "missing_ingredients": ["chocolate", "butter"],
  "scenario": "scenario_6"
}
```

**Example Input (No match)**:
```json
{
  "inventory": ["rice", "vegetables", "soy sauce"],
  "requested_ingredients": ["pasta", "cheese", "tomato sauce"],
  "missing_ingredients": ["pasta", "cheese", "tomato sauce"],
  "scenario": "scenario_6"
}
```

---

## Data Generation Pipeline

### 1. Groq API Configuration
- **Model**: Llama 3.1 8B
- **Temperature**: 0.7 (balanced creativity)
- **Max tokens**: 2048
- **Response format**: JSON
- **Rate limit**: Concurrent batch processing with retry logic

### 2. Prompt Engineering
Each scenario uses a carefully crafted prompt template:
- Clear instruction format
- JSON output structure specification
- Dietary constraint enforcement
- Cultural authenticity guidelines

### 3. Quality Controls
- JSON validation
- Dietary constraint verification
- Ingredient hallucination prevention
- Retry logic for API failures

---

## Why These 6 Scenarios?

### Coverage
- **Basic to complex**: From simple inventory usage to multi-constraint generation
- **Real-world patterns**: Covers actual user behavior in recipe apps
- **Edge cases**: Handles missing ingredients and constraint conflicts

### Diversity
- **Cultural variety**: 6 cuisines × multiple preferences
- **Constraint combinations**: Tests model under various restrictions
- **Ingredient flexibility**: From 5 to 10 ingredients per recipe

### Practical Value
- **Dietary safety**: Ensures allergen and preference compliance
- **User experience**: Handles unavailable ingredients gracefully
- **Cultural authenticity**: Respects cuisine traditions while allowing creativity

---

## Next Steps

After generation:
1. **Validation** → `03_validation/validate_dietary_constraints.py`
2. **Chat Format Conversion** → `02_chat_conversion/convert_to_chat_format.py`
3. **Training** → `04_training/lambda_finetune_llama3b.ipynb`

See [main README](../../README.md) for complete pipeline documentation.
