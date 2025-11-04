import time, json
from ollama import chat

models = [
    "gemma:2b",
    "llama3.2:3b-instruct-q4_K_M",
    # "phi3:mini",
    # "mistral:7b-instruct",
    # "qwen2.5:7b-instruct"
]

prompts = [
    "Generate a vegan pasta recipe under 30 minutes.",
    "Write a simple 5-ingredient vegan pasta recipe for beginners.",
]

records = []

for model in models:
    print(f"\nStarting model: {model} ===")
    for prompt in prompts:
        print(f"  Prompt: {prompt}")
        for run_idx in range(1, 4):
            print(f"    Run {run_idx}...", end="", flush=True)
            start = time.time()
            
            resp = chat(model=model, messages=[{"role": "user", "content": prompt}])
            latency = time.time() - start
            output_text = resp['message']['content']
            
            token_count = len(output_text.split())

            records.append({
                "model": model,
                "prompt": prompt,
                "output": output_text,
                "latency_sec": round(latency, 2),
                "token_count": token_count,
            })
            
            print(f" done ({round(latency,2)}s, {token_count} tokens)")

json.dump(records, open("ollama_eval_results.json", "w"), indent=2)
print("\nsaved to ollama_eval_results.json")