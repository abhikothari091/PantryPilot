# Use NVIDIA CUDA runtime as the base image
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Set the working directory inside the container
WORKDIR /app

# Install Python, pip, and git in the container
RUN apt-get update && apt-get install -y python3 python3-pip git && apt-get clean
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Copy the requirements.txt to the container and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the files from the local folder to the container
COPY . .

# Download base LLaMA model into /app/models/llama_base
RUN python3 -c "from transformers import AutoTokenizer, AutoModelForCausalLM; import os; \
model_id = 'meta-llama/Llama-3.2-3B-Instruct'; \
target = '/app/models/llama_base'; \
os.makedirs(target, exist_ok=True); \
print('Downloading Llama 3B base model...'); \
AutoTokenizer.from_pretrained(model_id).save_pretrained(target); \
AutoModelForCausalLM.from_pretrained(model_id).save_pretrained(target); \
print('Base model downloaded to', target)"

# Expose the port on which the app will run
EXPOSE 7860

# Set the entry point to start the Uvicorn server with FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
