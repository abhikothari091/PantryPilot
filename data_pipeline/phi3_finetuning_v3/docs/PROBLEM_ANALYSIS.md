# Problem Analysis: Dietary Constraint Violation in Production

## Executive Summary

A fine-tuned Phi-3 Mini model achieved 97.8% validation accuracy but failed dietary constraint checks in production, incorrectly selecting meat ingredients for vegetarian recipes. This document provides a comprehensive analysis of the root causes and the solution approach.

## The Problem

### Symptoms
- **Validation Performance**: 97.8% accuracy on held-out validation set
- **Production Failure**: Model selects `chicken breast` for vegetarian recipes
- **Inconsistency**: Same model architecture, different behavior in production

### Example Failure Case

```python
# Production Input
{
  "dietary": "vegetarian",
  "inventory": [
    "tomato",
    "onion",
    "garlic",
    "chicken breast",  # FORBIDDEN for vegetarian
    "olive oil",
    "pasta"
  ],
  "user_request": "I want a healthy vegetarian dinner"
}

# Model Output (WRONG)
{
  "selected_ingredients": [
    "tomato",
    "onion",
    "garlic",
    "chicken breast",  # ❌ SELECTED FORBIDDEN ITEM
    "olive oil",
    "pasta"
  ]
}
```

## Root Cause Analysis

### 1. Distribution Shift

**Training Data Distribution**:
- Chicken stock: 11.5% presence in vegetarian samples
- Chicken breast: <1% presence
- Most vegetarian samples: No meat at all

**Production Data Distribution**:
- Chicken breast: 17% presence (users' actual inventory)
- Diverse meat types: Beef, pork, fish, seafood
- Real-world scenario: Users have mixed inventories

**Impact**:
- Model learned to avoid "chicken stock" specifically
- Never learned to avoid "chicken breast" in vegetarian context
- No generalization to other meat/fish types

### 2. Training Data Analysis

#### Vegetarian Samples with Forbidden Items

**Original Dataset (V2)**:
```
Total vegetarian samples: 849
Samples with chicken stock: 849 (100%)
Samples with chicken breast: 0
Samples with other meat: 0
```

**Key Finding**: All 849 samples correctly avoided chicken stock, but:
- ❌ Zero diversity in forbidden items
- ❌ No exposure to chicken breast
- ❌ No exposure to beef, pork, fish, seafood
- ❌ Model learned specific token "chicken stock" rather than concept "meat"

#### Validation Set Bias

The validation set had the same distribution:
- Same 11.5% chicken stock presence
- Zero chicken breast
- Zero other meat types

**Result**: Model appeared to perform well (97.8%) but was actually overfit to this specific distribution.

### 3. Over-aggressive Fine-tuning

**V2 Hyperparameters**:
```python
learning_rate = 1e-4      # Too high
epochs = 3                # Too many
lora_alpha = 20           # Too aggressive
batch_size = 2            # Standard
```

**Impact**:
- Quick convergence to training distribution
- Strong memorization of specific tokens
- Limited generalization ability
- Overfitting to "chicken stock" pattern

### 4. Lack of Negative Examples

**Training Pattern**:
```
Input: vegetarian + [chicken stock, tomato, onion]
Output: [tomato, onion]  # Correctly avoids chicken stock
```

**Missing Pattern**:
```
Input: vegetarian + [chicken breast, tomato, onion]
Output: ???  # Model never saw this!
```

**Consequence**: Model had no opportunity to learn that:
- "chicken breast" = meat = forbidden for vegetarian
- "beef" = meat = forbidden for vegetarian
- "fish" = animal product = forbidden for vegetarian/vegan

## Why High Validation Accuracy?

### The Illusion of Success

**Validation Set Composition**:
- Same distribution as training set
- Same 11.5% chicken stock presence
- Same lack of chicken breast / other meats

**What Validation Actually Measured**:
- ✅ Can the model avoid "chicken stock" specifically?
- ❌ NOT: Can the model understand "vegetarian" constraint?
- ❌ NOT: Can the model generalize to unseen meat types?

**This is a classic case of overfitting to distribution, not concept**.

## Comparison: V2 vs V3

### Data Distribution

| Aspect | V2 (Failed) | V3 (Solution) |
|--------|-------------|---------------|
| Total samples | 4,059 | 5,000 |
| Vegetarian samples | 849 | 1,500 |
| Samples with meat in inventory | 849 (100% chicken stock) | 600 (diverse meats) |
| Meat diversity | 1 type | 5 categories (15+ items) |
| Augmentation strategy | Natural occurrence | Deliberate diverse augmentation |

### Training Configuration

| Parameter | V2 | V3 | Impact |
|-----------|----|----|--------|
| Learning Rate | 1e-4 | 5e-5 | Slower, more stable learning |
| Epochs | 3 | 2 | Less overfitting |
| LoRA Alpha | 20 | 16 | Reduced magnitude of changes |
| Batch Size | 2-4 | 1 | More memory safe |

### Augmentation Strategy

**V2 Approach**:
- Passive: Use whatever meat appears naturally in Recipe1M
- Result: 100% chicken stock, no diversity

**V3 Approach**:
- Active: Deliberately add diverse meat/fish to 40% of vegetarian samples
- Categories:
  1. **Poultry**: chicken breast, chicken thigh, turkey, duck
  2. **Beef**: ground beef, steak, sirloin, ribeye
  3. **Pork**: bacon, pork chops, ham, sausage
  4. **Fish**: salmon, tuna, cod, tilapia
  5. **Seafood**: shrimp, crab, lobster, scallops
- Per sample: 2-3 diverse items from different categories
- All marked as `forbidden: true`

## Validation of Solution

### Augmented Sample Verification

After V3 data generation:
```
Total vegetarian samples: 1,500
Augmented samples: 600 (40%)
Total forbidden items: 1,500+ (avg 2.5 per sample)

Verification Results:
- Samples with violations: 0
- Samples correctly avoiding forbidden: 600 (100%)
- Violation rate: 0.0%
```

### Expected Improvements

1. **Generalization**: Model will learn concept "meat" not just token "chicken stock"
2. **Robustness**: Exposure to 15+ different meat/fish types
3. **Stability**: Conservative training prevents overfitting
4. **Production Alignment**: Training distribution matches production distribution

## Lessons Learned

### 1. Distribution Matters More Than Accuracy

**Mistake**: Trusting 97.8% validation accuracy
**Reality**: Validation set had same bias as training set
**Lesson**: Always check if validation distribution matches production

### 2. Diversity is Critical for Constraints

**Mistake**: Relying on natural occurrence of forbidden items
**Reality**: Natural data had zero diversity (100% chicken stock)
**Lesson**: Deliberately augment with diverse negative examples

### 3. High Learning Rate + Few Data = Overfitting

**Mistake**: Learning rate 1e-4 with only 4,059 samples
**Reality**: Model quickly overfit to specific tokens
**Lesson**: Use conservative hyperparameters for small datasets

### 4. Test Production-Like Scenarios

**Mistake**: Only testing with validation set (same distribution)
**Reality**: Production had chicken breast (17%), not chicken stock (11.5%)
**Lesson**: Create test cases that mirror actual production distribution

## Conclusion

The production failure was not due to model architecture or training process, but rather:

1. **Distribution Shift**: Training had chicken stock, production had chicken breast
2. **Lack of Diversity**: Zero exposure to diverse meat/fish types
3. **Over-aggressive Training**: High learning rate led to overfitting
4. **Validation Bias**: Validation set had same distribution as training

V3 addresses all four issues through:
- Diverse meat/fish augmentation (5 categories, 15+ items)
- Conservative training (lower LR, fewer epochs)
- Balanced dataset (5,000 samples, 10 cuisines)
- Zero-violation validation (100% clean data)

---

**Status**: V3 training in progress
**Expected**: Robust generalization to all meat/fish types in production
