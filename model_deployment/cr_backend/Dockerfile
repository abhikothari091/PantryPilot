FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python + pip
RUN apt-get update && apt-get install -y python3 python3-pip git && apt-get clean
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Install gsutil
RUN apt-get update && apt-get install -y python3-pip && pip install gsutil

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Download LLaMA model from GCS into /app/models/llama_basee
RUN gsutil -m cp -r gs://pantrypilot-bucket/llama_base /app/models/

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
