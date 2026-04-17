# 🤖 BuildRight Managed PR
This Pull Request is managed by BuildRight AI.

## 💡 How to iterate
You can talk to the AI directly by posting a comment on this PR:
- `/fix [issue]` — Fix a specific bug or visual issue.
- `/revise [logic]` — Update the behavior or logic.
- `/update [context]` — Add more information for the AI to consider.

BuildRight will automatically process your command, analyze the scope, and push a new commit back to this branch.

---

## 🚫 Hidden-Gluten Blocklist — Feature Summary

### What was changed
This PR adds a static **hidden-gluten ingredient blocklist** to `model_deployment/backend/model_service.py` and injects it into the LLM system prompt whenever a user's dietary profile includes a gluten-free restriction.

### Blocklist (`HIDDEN_GLUTEN_BLOCKLIST`)
The following 15 ingredients are flagged as hidden gluten sources and are explicitly forbidden in the generated prompt:

| Ingredient | Why it's hidden |
|---|---|
| soy sauce | traditionally brewed with wheat |
| wheat starch | direct wheat derivative |
| malt vinegar | barley-derived |
| barley malt | contains gluten |
| regular oats | cross-contaminated unless certified GF |
| seitan | made from wheat gluten |
| teriyaki sauce | contains soy sauce (wheat) |
| hoisin sauce | contains wheat flour |
| oyster sauce | often thickened with wheat starch |
| worcestershire sauce | contains malt vinegar |
| malt extract | barley-derived |
| spelt | ancient wheat variety |
| kamut | ancient wheat variety |
| farro | wheat species |
| bulgur | cracked wheat |

### How it works
1. When `generate_recipe()` is called with a preference that contains `"gluten"` (e.g. `"gluten-free"`), the service appends two constraint lines to `strict_restrictions`:
   - `ABSOLUTELY NO gluten (no wheat, barley, rye, regular pasta, bread, flour)`
   - `HIDDEN GLUTEN SOURCES — DO NOT USE (these contain gluten despite appearing safe): <blocklist>`
2. These restrictions are embedded in the `⚠️ MANDATORY RESTRICTIONS` block that is prepended to both `custom_preferences` and the `user_request` payload sent to the external LLM API.
3. A log line is printed to backend stdout at the point of injection:
   ```
   🚫 Gluten-free profile detected — injecting hidden-gluten blocklist: soy sauce, wheat starch, ...
   ```

### Verifying in logs
Search backend logs for:
```
🚫 Gluten-free profile detected — injecting hidden-gluten blocklist
```
This line is emitted once per `generate_recipe` call where gluten-free is active.

### Tests added (`tests/backend/test_recipes.py`)
| Test | What it checks |
|---|---|
| `test_gluten_free_profile_injects_blocklist` | Calls `/recipes/generate` with a gluten-free profile via the HTTP client and asserts the dietary restriction is forwarded correctly. |
| `test_gluten_free_blocklist_content_in_prompt` | Directly instantiates `ModelService`, patches `requests.post`, and asserts every blocklist item appears in the constructed payload. Also asserts `len(HIDDEN_GLUTEN_BLOCKLIST) >= 10`. |
| `test_non_gluten_free_profile_no_blocklist` | Runs the same flow with a `vegan` profile and confirms the blocklist items are **not** present in the payload. |

---
*Created by [BuildRight](https://buildrightai.app)*
