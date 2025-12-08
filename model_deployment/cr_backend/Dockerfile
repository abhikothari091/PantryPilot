FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python + pip
RUN apt-get update && apt-get install -y python3 python3-pip git && apt-get clean
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Add Hugging Face token to authenticate
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

# Download base LLaMA model into /app/models/llama_base using the Hugging Face token (Single line)
RUN python3 -c "from transformers import AutoTokenizer, AutoModelForCausalLM; from huggingface_hub import login; import os; login(token=os.getenv('HF_TOKEN')); model_id = 'meta-llama/Llama-3.2-3B-Instruct'; target = '/app/models/llama_base'; os.makedirs(target, exist_ok=True); print('Downloading Llama 3B base model...'); AutoTokenizer.from_pretrained(model_id).save_pretrained(target); AutoModelForCausalLM.from_pretrained(model_id).save_pretrained(target); print('Base model downloaded to', target)"

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
