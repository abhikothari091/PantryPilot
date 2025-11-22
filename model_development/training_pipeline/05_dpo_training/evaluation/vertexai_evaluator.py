"""
Vertex AI Evaluator for DPO Persona Models

Uses Google Cloud's Vertex AI to evaluate recipe generation models:
- Claude 3.5 Sonnet/Haiku (Anthropic via Model Garden)
- Gemini 1.5 Flash/Pro (Google)
- Llama 3.1/3.2 (Meta via Model Garden)

Provides unified interface for multi-model evaluation and comparison.
"""

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time


class VertexAIEvaluator:
    """
    Evaluate SFT vs DPO recipes using Vertex AI models

    Supports multiple evaluator models:
    - gemini-2.0-flash-exp: Fastest, latest Gemini 2.0 (experimental)
    - gemini-2.5-pro: Best quality Gemini (stable)
    - claude-3-5-haiku@20241022: Fast, high quality
    - claude-3-5-sonnet@20241022: Best quality
    """

    # Available models (Updated to Gemini 2.0 - Gemini 1.5 deprecated)
    MODELS = {
        "gemini-flash": "gemini-2.0-flash-exp",     # Gemini 2.0 Flash (experimental, latest)
        "gemini-pro": "gemini-2.5-pro",             # Gemini 2.5 Pro (latest stable)
        "claude-haiku": "claude-3-5-haiku@20241022",
        "claude-sonnet": "claude-3-5-sonnet@20241022",
    }

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        evaluator_model: str = "claude-haiku"
    ):
        """
        Initialize Vertex AI evaluator

        Args:
            project_id: GCP project ID
            location: GCP region (default: us-central1)
            evaluator_model: Model to use (gemini-flash, claude-haiku, etc.)
        """
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Get model identifier
        if evaluator_model not in self.MODELS:
            raise ValueError(
                f"Unknown model: {evaluator_model}. "
                f"Available: {list(self.MODELS.keys())}"
            )

        model_id = self.MODELS[evaluator_model]
        self.model = GenerativeModel(model_id)
        self.evaluator_name = evaluator_model
        self.model_id = model_id

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

        print(f"✅ Initialized {evaluator_model} ({model_id})")

    def _rate_limit(self):
        """Ensure minimum time between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def evaluate_recipe_pair(
        self,
        persona_config: Dict,
        recipe_sft: str,
        recipe_dpo: str,
        inventory: List[str],
        user_request: str
    ) -> Dict:
        """
        Evaluate which recipe better matches persona preferences

        Args:
            persona_config: Persona definition from personas.yaml
            recipe_sft: SFT model recipe (JSON string)
            recipe_dpo: DPO persona model recipe (JSON string)
            inventory: List of ingredients available
            user_request: Original user request

        Returns:
            Dictionary with evaluation results:
            {
                "winner": "sft" or "dpo",
                "sft_score": 0-10,
                "dpo_score": 0-10,
                "confidence": "high" or "medium" or "low",
                "reasoning": "explanation",
                "violations": {
                    "sft": [...],
                    "dpo": [...]
                },
                "evaluator": "model name"
            }
        """
        prompt = self._build_evaluation_prompt(
            persona_config,
            recipe_sft,
            recipe_dpo,
            inventory,
            user_request
        )

        try:
            # Rate limiting
            self._rate_limit()

            # Generation config
            generation_config = GenerationConfig(
                temperature=0.2,  # Low temp for consistent evaluation
                max_output_tokens=1000,
            )

            # Call Vertex AI
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Parse response
            evaluation = self._parse_evaluation(response.text)
            evaluation["evaluator"] = self.evaluator_name

            return evaluation

        except Exception as e:
            print(f"\n⚠️  Vertex AI Error ({self.evaluator_name}): {e}")
            return {
                "error": str(e),
                "winner": "unknown",
                "sft_score": 0,
                "dpo_score": 0,
                "confidence": "none",
                "reasoning": f"Evaluation failed: {e}",
                "evaluator": self.evaluator_name
            }

    def _build_evaluation_prompt(
        self,
        persona: Dict,
        recipe_sft: str,
        recipe_dpo: str,
        inventory: List[str],
        user_request: str
    ) -> str:
        """Build evaluation prompt for Vertex AI"""

        # Parse recipes if they're JSON strings
        try:
            if isinstance(recipe_sft, str):
                recipe_sft_obj = json.loads(recipe_sft)
            else:
                recipe_sft_obj = recipe_sft
                recipe_sft = json.dumps(recipe_sft, indent=2, ensure_ascii=False)
        except:
            recipe_sft_obj = None

        try:
            if isinstance(recipe_dpo, str):
                recipe_dpo_obj = json.loads(recipe_dpo)
            else:
                recipe_dpo_obj = recipe_dpo
                recipe_dpo = json.dumps(recipe_dpo, indent=2, ensure_ascii=False)
        except:
            recipe_dpo_obj = None

        forbidden = ", ".join(persona.get("forbidden_keywords", []))
        preferences = ", ".join(persona.get("preference_keywords", []))
        cuisines = ", ".join(persona.get("preferences", {}).get("cuisine", []))
        flavors = ", ".join(persona.get("preferences", {}).get("flavor_profile", []))
        restrictions = ", ".join(persona.get("dietary_restrictions", []))

        return f"""You are evaluating two recipe generation models for persona alignment.

**Persona Profile:**
Name: {persona['name']}
Preferred Cuisines: {cuisines}
Flavor Profile: {flavors}
Cooking Style: {persona.get('preferences', {}).get('cooking_style', 'any')}
Dietary Restrictions: {restrictions or 'None'}
Forbidden Ingredients: {forbidden or 'None'}
Preferred Keywords: {preferences}

**Context:**
Available Inventory: {', '.join(inventory)}
User Request: {user_request}

**Recipe A (SFT Baseline Model):**
```json
{recipe_sft}
```

**Recipe B (DPO Persona Model):**
```json
{recipe_dpo}
```

**Evaluation Task:**

Rate each recipe on the following criteria (0-10 scale):

1. **Persona Alignment** (0-10): Does the recipe match the persona's cuisine and style preferences?
2. **Constraint Compliance** (0-10): Does it avoid forbidden ingredients and respect dietary restrictions?
3. **Preferred Ingredients** (0-10): Does it use ingredients the persona prefers?
4. **Recipe Quality** (0-10): Is it practical, well-structured, and coherent?
5. **Overall Fit** (0-10): How well does this recipe represent the persona?

**Important Evaluation Guidelines:**
- Forbidden ingredients are CRITICAL violations (deduct heavily)
- Dietary restrictions must be respected (vegetarian, vegan, gluten-free, etc.)
- Preferred cuisine match is important but not required if inventory doesn't support it
- Recipe quality matters: clear steps, reasonable ingredient amounts, coherent instructions

**Output Format (JSON only):**
```json
{{
  "recipe_a_scores": {{
    "persona_alignment": <0-10>,
    "constraint_compliance": <0-10>,
    "preferred_ingredients": <0-10>,
    "recipe_quality": <0-10>,
    "overall_fit": <0-10>
  }},
  "recipe_b_scores": {{
    "persona_alignment": <0-10>,
    "constraint_compliance": <0-10>,
    "preferred_ingredients": <0-10>,
    "recipe_quality": <0-10>,
    "overall_fit": <0-10>
  }},
  "winner": "A" or "B",
  "confidence": "high" or "medium" or "low",
  "reasoning": "Brief explanation of why the winner is better (2-3 sentences)",
  "violations_found": {{
    "recipe_a": ["list of forbidden ingredients found, if any"],
    "recipe_b": ["list of forbidden ingredients found, if any"]
  }}
}}
```

**Confidence Guidelines:**
- "high": Clear winner, score difference > 3 points
- "medium": Noticeable difference, score difference 2-3 points
- "low": Very similar, score difference < 2 points

IMPORTANT: Respond with ONLY valid JSON. No additional text before or after."""

    def _parse_evaluation(self, response_text: str) -> Dict:
        """Parse evaluation response from Vertex AI"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                evaluation_data = json.loads(json_match.group(0))

                # Calculate average scores
                recipe_a_scores = evaluation_data.get("recipe_a_scores", {})
                recipe_b_scores = evaluation_data.get("recipe_b_scores", {})

                sft_avg = sum(recipe_a_scores.values()) / len(recipe_a_scores) if recipe_a_scores else 0
                dpo_avg = sum(recipe_b_scores.values()) / len(recipe_b_scores) if recipe_b_scores else 0

                # Determine winner
                winner_letter = evaluation_data.get("winner", "").upper()
                winner = "sft" if winner_letter == "A" else "dpo" if winner_letter == "B" else "unknown"

                return {
                    "winner": winner,
                    "sft_score": round(sft_avg, 2),
                    "dpo_score": round(dpo_avg, 2),
                    "sft_scores_detail": recipe_a_scores,
                    "dpo_scores_detail": recipe_b_scores,
                    "confidence": evaluation_data.get("confidence", "unknown"),
                    "reasoning": evaluation_data.get("reasoning", ""),
                    "violations": evaluation_data.get("violations_found", {"recipe_a": [], "recipe_b": []}),
                    "raw_evaluation": evaluation_data
                }
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"⚠️  Parse error: {e}")
            print(f"Response text: {response_text[:200]}...")

            return {
                "winner": "unknown",
                "sft_score": 0,
                "dpo_score": 0,
                "confidence": "none",
                "reasoning": f"Failed to parse response: {e}",
                "violations": {"recipe_a": [], "recipe_b": []},
                "parse_error": str(e),
                "raw_response": response_text[:500]
            }

    def batch_evaluate(
        self,
        test_cases: List[Dict],
        persona_config: Dict,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Evaluate multiple test cases for a persona

        Args:
            test_cases: List of test case dictionaries with keys:
                - recipe_sft: SFT model output
                - recipe_dpo: DPO model output
                - inventory: ingredients list
                - user_request: user's request
            persona_config: Persona definition
            verbose: Print progress

        Returns:
            List of evaluation results
        """
        results = []

        for i, case in enumerate(test_cases):
            if verbose:
                print(f"  [{i+1}/{len(test_cases)}] Evaluating with {self.evaluator_name}...", end="\r")

            evaluation = self.evaluate_recipe_pair(
                persona_config=persona_config,
                recipe_sft=case["recipe_sft"],
                recipe_dpo=case["recipe_dpo"],
                inventory=case["inventory"],
                user_request=case["user_request"]
            )

            results.append({
                "test_case_id": i + 1,
                "evaluation": evaluation,
                "metadata": case.get("metadata", {})
            })

        if verbose:
            print()  # New line after progress

        return results


class MultiModelEvaluator:
    """
    Run evaluation across multiple Vertex AI models for cross-validation
    """

    def __init__(self, project_id: str, location: str = "us-central1"):
        """
        Initialize multi-model evaluator

        Args:
            project_id: GCP project ID
            location: GCP region
        """
        self.project_id = project_id
        self.location = location
        self.evaluators = {}

    def add_evaluator(self, name: str, model: str):
        """
        Add an evaluator model

        Args:
            name: Friendly name (e.g., "gemini", "claude-haiku")
            model: Model identifier from VertexAIEvaluator.MODELS
        """
        evaluator = VertexAIEvaluator(
            project_id=self.project_id,
            location=self.location,
            evaluator_model=model
        )
        self.evaluators[name] = evaluator
        return evaluator

    def evaluate_with_all(
        self,
        persona_config: Dict,
        recipe_sft: str,
        recipe_dpo: str,
        inventory: List[str],
        user_request: str
    ) -> Dict:
        """
        Evaluate with all configured evaluators

        Returns:
            {
                "evaluations": {model_name: evaluation_result},
                "consensus": {...},
                "agreement": {...}
            }
        """
        evaluations = {}

        for name, evaluator in self.evaluators.items():
            evaluation = evaluator.evaluate_recipe_pair(
                persona_config=persona_config,
                recipe_sft=recipe_sft,
                recipe_dpo=recipe_dpo,
                inventory=inventory,
                user_request=user_request
            )
            evaluations[name] = evaluation

        # Compute consensus
        consensus = self._compute_consensus(evaluations)

        return {
            "evaluations": evaluations,
            "consensus": consensus,
            "agreement": self._compute_agreement(evaluations)
        }

    def _compute_consensus(self, evaluations: Dict) -> Dict:
        """Compute consensus across evaluators"""
        winners = [e["winner"] for e in evaluations.values() if e["winner"] != "unknown"]

        if not winners:
            return {"winner": "unknown", "confidence": "none"}

        # Count votes
        sft_votes = winners.count("sft")
        dpo_votes = winners.count("dpo")

        # Determine consensus
        if sft_votes > dpo_votes:
            consensus_winner = "sft"
            confidence = "high" if sft_votes == len(winners) else "medium"
        elif dpo_votes > sft_votes:
            consensus_winner = "dpo"
            confidence = "high" if dpo_votes == len(winners) else "medium"
        else:
            consensus_winner = "tie"
            confidence = "low"

        return {
            "winner": consensus_winner,
            "confidence": confidence,
            "votes": {"sft": sft_votes, "dpo": dpo_votes},
            "agreement_rate": max(sft_votes, dpo_votes) / len(winners) if winners else 0
        }

    def _compute_agreement(self, evaluations: Dict) -> Dict:
        """Compute agreement metrics across evaluators"""
        winners = [e["winner"] for e in evaluations.values() if e["winner"] != "unknown"]

        if len(winners) < 2:
            return {"agreement": "insufficient_data"}

        # Check if all agree
        all_agree = len(set(winners)) == 1

        # Check if majority agrees
        from collections import Counter
        counts = Counter(winners)
        majority_winner, majority_count = counts.most_common(1)[0]

        return {
            "all_agree": all_agree,
            "majority_winner": majority_winner,
            "majority_count": majority_count,
            "total_evaluators": len(winners),
            "agreement_rate": majority_count / len(winners) if winners else 0
        }


if __name__ == "__main__":
    # Test the evaluator
    import yaml

    # Load personas
    personas_file = Path(__file__).parent.parent / "data_pipeline/05_dpo_training/personas.yaml"
    with open(personas_file) as f:
        personas = yaml.safe_load(f)['personas']

    # Test with persona A
    persona = personas['persona_a_korean_spicy']

    # Mock recipes
    recipe_sft = json.dumps({
        "recipe": {
            "name": "Chicken Rice Bowl",
            "cuisine": "asian",
            "ingredients": ["chicken", "rice", "onion", "garlic"],
            "steps": ["Cook rice", "Stir-fry chicken with garlic and onion"]
        }
    })

    recipe_dpo = json.dumps({
        "recipe": {
            "name": "Spicy Korean Chicken with Gochujang",
            "cuisine": "korean",
            "ingredients": ["chicken", "rice", "gochujang", "garlic", "sesame oil"],
            "steps": ["Marinate chicken with gochujang", "Stir-fry with garlic", "Drizzle with sesame oil"]
        }
    })

    # Initialize evaluator (requires GCP auth)
    try:
        evaluator = VertexAIEvaluator(
            project_id="your-gcp-project",  # Replace with actual project
            evaluator_model="gemini-flash"
        )

        result = evaluator.evaluate_recipe_pair(
            persona_config=persona,
            recipe_sft=recipe_sft,
            recipe_dpo=recipe_dpo,
            inventory=["chicken", "rice", "gochujang", "garlic"],
            user_request="Make me a Korean recipe"
        )

        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Test failed (expected if GCP not configured): {e}")
