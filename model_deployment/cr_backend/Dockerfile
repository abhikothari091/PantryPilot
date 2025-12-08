FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

RUN apt-get update && apt-get install -y python3 python3-pip git && apt-get clean
RUN ln -sf /usr/bin/python3 /usr/bin/python

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download base LLaMA model into /app/models/llama_base in a single line
RUN python3 -c "from transformers import AutoTokenizer, AutoModelForCausalLM; import os; model_id = 'meta-llama/Llama-3.2-3B-Instruct'; target = '/app/models/llama_base'; os.makedirs(target, exist_ok=True); print('Downloading Llama 3B base model...'); AutoTokenizer.from_pretrained(model_id).save_pretrained(target); AutoModelForCausalLM.from_pretrained(model_id).save_pretrained(target); print('Base model downloaded to', target)"

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
