# Chat Format Conversion

Converts synthetic recipe data from structured JSON to **Llama 3 chat format** for fine-tuning.

## Purpose

Fine-tuning requires data in a conversational format with proper special tokens:
- `<|begin_of_text|>` - Start of conversation
- `<|start_header_id|>system<|end_header_id|>` - System instruction
- `<|start_header_id|>user<|end_header_id|>` - User request
- `<|start_header_id|>assistant<|end_header_id|>` - Model response
- `<|eot_id|>` - End of turn

## Files

- `convert_to_chat_format.py` - Conversion script

## Usage

```bash
python convert_to_chat_format.py \
  --input data/synthetic/recipes_12k.jsonl \
  --output data/chat_format/recipes_chat.jsonl
```

## Input Format

Structured JSON from synthetic generation:

```json
{
  "input": {
    "user_inventory": ["chicken", "rice", "soy sauce"],
    "preference": "None",
    "cuisine": "Chinese"
  },
  "output": {
    "recipe_name": "Chicken Fried Rice",
    "ingredients": [...],
    "instructions": [...]
  }
}
```

## Output Format

Llama 3 chat format:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful recipe assistant. Generate recipes based on available ingredients and dietary constraints."
    },
    {
      "role": "user",
      "content": "Generate a recipe using these ingredients: chicken, rice, soy sauce\nDietary constraints: None\nCuisine preference: Chinese"
    },
    {
      "role": "assistant",
      "content": "Recipe Name: Chicken Fried Rice\n\nIngredients:\n- chicken: 200g\n- rice: 2 cups\n..."
    }
  ]
}
```

## Chat Template

The exact template used for Llama 3.2 3B Instruct:

```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful recipe assistant. Generate recipes based on available ingredients and dietary constraints.<|eot_id|><|start_header_id|>user<|end_header_id|>

Generate a recipe using these ingredients: {ingredients}
Dietary constraints: {constraints}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{recipe}<|eot_id|>
```

## Dietary Constraint Handling

The conversion process **enforces dietary constraints in the system prompt**:

### Vegan
```
IMPORTANT: This recipe must be VEGAN. Do not use any animal products including:
- Meat, poultry, fish, seafood
- Dairy (milk, cheese, butter, cream, yogurt)
- Eggs
- Honey
```

### Vegetarian
```
IMPORTANT: This recipe must be VEGETARIAN. Do not use:
- Meat, poultry, fish, seafood
- Gelatin or any meat-based products
```

### Gluten-free
```
IMPORTANT: This recipe must be GLUTEN-FREE. Do not use:
- Wheat, flour, bread, pasta
- Barley, rye
- Soy sauce (use gluten-free alternatives)
```

### Dairy-free
```
IMPORTANT: This recipe must be DAIRY-FREE. Do not use:
- Milk, butter, cream, cheese, yogurt
- Any dairy-based products
```

## Statistics

After conversion, the script outputs:
- Total conversations converted
- Distribution by scenario
- Token statistics (min/max/avg)
- Validation errors (if any)

## Quality Checks

1. **Format validation** - Ensures proper chat structure
2. **Token verification** - Checks special tokens are correctly placed
3. **Constraint preservation** - Verifies dietary constraints in prompts

## Next Steps

After conversion:
1. **Validate constraints** → `../03_validation/validate_dietary_constraints.py`
2. **Clean data** → `../03_validation/clean_training_data.py`
3. **Train model** → `../04_training/lambda_finetune_llama3b.ipynb`

## Why Chat Format?

Modern LLMs are trained on conversational data. Chat format:
- **Improves instruction following** - Clear role separation
- **Better generalization** - Matches inference format
- **Explicit constraints** - System prompts enforce rules
- **Standard format** - Compatible with Hugging Face trainers
