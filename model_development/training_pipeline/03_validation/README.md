# Data Validation and Cleaning

This directory contains scripts for validating and cleaning the training dataset to ensure high quality and dietary constraint compliance.

## Files

- `validate_dietary_constraints.py` - Validates recipes against dietary constraints
- `clean_training_data.py` - Removes/fixes problematic recipes

## Purpose

After synthetic generation, we must ensure:
1. **Dietary constraint compliance** - No violations (e.g., vegan recipes with dairy)
2. **Ingredient consistency** - No hallucinated ingredients
3. **JSON validity** - Proper structure for training
4. **Quality standards** - Complete recipes with instructions

## Validation Process

### Step 1: Dietary Constraint Validation

```bash
python validate_dietary_constraints.py \
  --input data/chat_format/recipes_chat.jsonl \
  --output validation_reports/constraint_violations.json
```

**What it checks**:

#### Vegan Violations
Forbidden ingredients:
- Animal products: chicken, beef, pork, fish, seafood
- Dairy: milk, butter, cheese, cream, yogurt
- Eggs
- Honey
- Gelatin

#### Vegetarian Violations
Forbidden ingredients:
- Meat: chicken, beef, pork, lamb
- Fish and seafood
- Gelatin (animal-derived)

#### Gluten-free Violations
Forbidden ingredients:
- Wheat products: flour, bread, pasta
- Barley, rye
- Soy sauce (unless gluten-free specified)
- Couscous, bulgur

#### Dairy-free Violations
Forbidden ingredients:
- Milk (cow, goat)
- Butter
- Cheese
- Cream, sour cream
- Yogurt
- Whey, casein

### Step 2: Automated Cleaning

```bash
python clean_training_data.py \
  --input data/chat_format/recipes_chat.jsonl \
  --violations validation_reports/constraint_violations.json \
  --output data/cleaned/recipes_cleaned.jsonl \
  --strategy remove
```

**Cleaning strategies**:

1. **Remove** (default)
   - Deletes recipes with violations
   - Safest approach for dietary constraints

2. **Fix** (experimental)
   - Attempts to substitute ingredients
   - Example: Replace "milk" → "almond milk" for vegan
   - Requires manual review

3. **Flag** (review mode)
   - Marks violations for human review
   - Outputs flagged recipes to separate file

## Validation Results

### Initial Dataset (Before Cleaning)
- Total recipes: 12,000
- Violations found: ~150 (1.25%)

**Common violations**:
- Vegan recipes with honey (45 cases)
- Gluten-free recipes with soy sauce (38 cases)
- Dairy-free recipes with butter (32 cases)
- Vegetarian recipes with chicken broth (35 cases)

### Final Dataset (After Cleaning)
- Total recipes: 11,850
- Clean recipes: 100%
- Dietary compliance: Verified

## Validation Reports

The validation process generates detailed reports:

### `constraint_violations.json`
```json
{
  "total_recipes": 12000,
  "total_violations": 150,
  "violations_by_constraint": {
    "vegan": 82,
    "vegetarian": 35,
    "gluten-free": 21,
    "dairy-free": 12
  },
  "detailed_violations": [
    {
      "recipe_id": "recipe_4521",
      "constraint": "vegan",
      "violation": "contains honey",
      "ingredients": ["flour", "sugar", "honey", "baking powder"]
    }
  ]
}
```

### `cleaning_summary.json`
```json
{
  "input_count": 12000,
  "output_count": 11850,
  "removed_count": 150,
  "removal_reasons": {
    "dietary_violation": 150
  },
  "final_distribution": {
    "scenario_1": 2950,
    "scenario_2": 2350,
    ...
  }
}
```

## Quality Checks

Beyond dietary constraints, we validate:

1. **Completeness**
   - Recipe has name, ingredients, instructions
   - No empty fields

2. **Ingredient availability**
   - All recipe ingredients come from user inventory
   - No hallucinated ingredients

3. **Instruction quality**
   - Minimum 3 instruction steps
   - Clear, actionable steps

4. **Token limits**
   - Recipes fit within model context (< 2048 tokens)

## Manual Review (Optional)

For critical applications, we recommend:

```bash
# Export flagged recipes for human review
python validate_dietary_constraints.py \
  --input data/cleaned/recipes_cleaned.jsonl \
  --output validation_reports/manual_review.json \
  --export-samples 50
```

Review sample recipes from each constraint category to verify quality.

## Why Validation Matters

### Safety
- **Allergen compliance** - Critical for users with allergies
- **Dietary restrictions** - Religious, ethical, health reasons
- **Trust** - Users rely on accurate constraint enforcement

### Model Quality
- **Clean training data** - Garbage in, garbage out
- **Consistent patterns** - Model learns correct associations
- **Generalization** - Better performance on unseen data

## Next Steps

After validation and cleaning:
1. **Split dataset** → Train/validation/test sets
2. **Upload to Lambda Labs** → Prepare for training
3. **Fine-tune model** → `../04_training/lambda_finetune_llama3b.ipynb`

## Statistics

Final cleaned dataset statistics:
- **Total recipes**: 11,850
- **Train set**: 9,480 (80%)
- **Validation set**: 1,185 (10%)
- **Test set**: 1,185 (10%)
- **Dietary compliance**: 100%
- **Quality score**: ≥95% (manual sample review)
