# Synthetic Recipe Generation with Groq API

This directory contains scripts for generating synthetic recipe data using **Groq API (Llama 3.1 8B)**.

## Overview

We generated **12,000 synthetic recipes** across **6 diverse scenarios** to create a high-quality training dataset for recipe generation fine-tuning.

## Files

- `generate_synthetic_recipes_groq.py` - Main generation script
- `SCENARIOS.md` - Detailed documentation of 6 scenarios

## Requirements

```bash
pip install groq pyyaml tqdm
```

## Configuration

Create `config/synthetic_generation.yaml`:

```yaml
groq:
  model: "llama-3.1-8b-instant"
  temperature: 0.7
  max_tokens: 2048
  rate_limit: 30  # requests per minute
  batch_size: 10
  max_retries: 3

cuisines:
  - Italian
  - Chinese
  - Mexican
  - Indian
  - Japanese
  - Korean

preferences:
  - vegan
  - vegetarian
  - gluten-free
  - dairy-free

scenarios:
  scenario_2:
    distribution:
      vegan: 800
      vegetarian: 800
      gluten-free: 400
      dairy-free: 400

  scenario_3:
    distribution:
      Italian: 300
      Chinese: 300
      Mexican: 300
      Indian: 300
      Japanese: 300
      Korean: 300
```

## Usage

```bash
export GROQ_API_KEY="your_groq_api_key"

python generate_synthetic_recipes_groq.py \
  --config config/synthetic_generation.yaml \
  --output data/synthetic/recipes_12k.jsonl \
  --num-workers 5
```

## Output Format

Each generated recipe follows this structure:

```json
{
  "input": {
    "user_inventory": ["chicken", "rice", "soy sauce", "vegetables"],
    "requested_ingredients": null,
    "user_request": "",
    "preference": "None",
    "cuisine": "Chinese"
  },
  "output": {
    "recipe_name": "Chicken Fried Rice",
    "ingredients": [
      {"name": "chicken", "amount": "200g"},
      {"name": "rice", "amount": "2 cups"},
      {"name": "soy sauce", "amount": "2 tbsp"},
      {"name": "vegetables", "amount": "1 cup"}
    ],
    "instructions": [
      "Cook rice according to package instructions",
      "Dice chicken into small pieces",
      "..."
    ],
    "prep_time": "10 minutes",
    "cook_time": "15 minutes",
    "servings": 2
  },
  "scenario": "scenario_3",
  "generated_at": "2024-11-13T12:00:00Z"
}
```

## Generation Statistics

After completion, the script outputs:
- Total recipes generated
- Success/failure counts per scenario
- Average generation time
- Error logs

## Why Groq + Llama 3.1 8B?

### Groq Advantages
- **Speed**: 10-100x faster than OpenAI GPUs
- **Cost-effective**: Lower pricing for high-volume generation
- **Reliability**: High uptime and consistent performance

### Llama 3.1 8B
- **JSON output**: Native structured output support
- **Instruction following**: Strong adherence to prompts
- **Quality**: Comparable to GPT-3.5 for recipe generation
- **Open source**: Transparency in model capabilities

## Quality Assurance

The generation process includes:
1. **JSON validation** - Ensures parseable outputs
2. **Retry logic** - Handles API failures gracefully
3. **Rate limiting** - Prevents quota exhaustion
4. **Progress tracking** - Real-time monitoring with tqdm

## Next Steps

After generation:
1. **Validate data** → `../03_validation/validate_dietary_constraints.py`
2. **Convert to chat format** → `../02_chat_conversion/convert_to_chat_format.py`

See [SCENARIOS.md](SCENARIOS.md) for detailed scenario descriptions.
