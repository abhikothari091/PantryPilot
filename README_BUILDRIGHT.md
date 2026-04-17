# 🤖 BuildRight Managed PR
This Pull Request is managed by BuildRight AI.

## 💡 How to iterate
You can talk to the AI directly by posting a comment on this PR:
- `/fix [issue]` — Fix a specific bug or visual issue.
- `/revise [logic]` — Update the behavior or logic.
- `/update [context]` — Add more information for the AI to consider.

BuildRight will automatically process your command, analyze the scope, and push a new commit back to this branch.

---

## 🚫 Feature: Hidden-Gluten Blocklist & System Prompt Injection

### What changed
A static `HIDDEN_GLUTEN_BLOCKLIST` has been added to `model_deployment/backend/model_service.py`. When a user's dietary profile includes any gluten-free restriction, the full blocklist is automatically injected into the LLM prompt as an explicit **MANDATORY RESTRICTION** before the recipe request is sent to the external API.

### Why it matters
Many common ingredients appear safe but secretly contain gluten (e.g. soy sauce contains wheat). Without an explicit blocklist, the LLM may inadvertently suggest these ingredients even when a gluten-free diet is requested.

### Blocked ingredients (15 hidden-gluten sources)
| Ingredient | Why it contains gluten |
|---|---|
| Soy sauce | Traditionally brewed with wheat |
| Wheat starch | Derived directly from wheat |
| Malt vinegar | Made from barley malt |
| Barley malt | Contains gluten from barley |
| Regular oats | Cross-contaminated with wheat unless certified GF |
| Seitan | Made entirely from wheat gluten |
| Teriyaki sauce | Contains soy sauce (wheat) |
| Hoisin sauce | Contains wheat flour |
| Oyster sauce | Often thickened with wheat starch |
| Worcestershire sauce | May contain malt vinegar (barley) |
| Malt extract | Derived from barley |
| Spelt | Ancient wheat variety — contains gluten |
| Kamut | Ancient wheat variety — contains gluten |
| Farro | Ancient wheat variety — contains gluten |
| Bulgur | Cracked wheat — contains gluten |

### How it works
1. `generate_recipe()` in `model_service.py` checks whether any dietary restriction contains `"gluten"`.
2. If matched, it appends two entries to `strict_restrictions`:
   - `ABSOLUTELY NO gluten (no wheat, barley, rye, regular pasta, bread, flour)`
   - `HIDDEN GLUTEN SOURCES — DO NOT USE (these contain gluten despite appearing safe): <full blocklist>`
3. The restriction block is prepended to `custom_preferences` and also embedded in `user_request`, so both fields sent to the LLM carry the constraint.
4. A log line is emitted:
   ```
   🚫 Gluten-free profile detected — injecting hidden-gluten blocklist: soy sauce, wheat starch, ...
   ```

### Verifying in logs
Search backend logs for:
```
🚫 Gluten-free profile detected — injecting hidden-gluten blocklist
```
This line is printed every time the blocklist is injected, making it auditable per request.

### Tests added
| Test | File | What it verifies |
|---|---|---|
| `test_gluten_free_blocklist_content_in_prompt` | `tests/backend/test_recipes.py` | All 15 blocklist items appear in the payload sent to the LLM API |
| `test_gluten_free_profile_injects_blocklist` | `tests/backend/test_recipes.py` | The `generate_recipe` mock is called with gluten-free dietary restrictions when profile is set |
| `test_non_gluten_free_profile_no_blocklist` | `tests/backend/test_recipes.py` | Blocklist items are absent from the prompt for non-gluten-free profiles (e.g. vegan) |

---
*Created by [BuildRight](https://buildrightai.app)*
