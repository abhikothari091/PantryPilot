FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python + pip and gcloud
RUN apt-get update && apt-get install -y python3 python3-pip git curl apt-transport-https ca-certificates gnupg && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && apt-get install -y google-cloud-sdk

# Install dependencies from requirements.txt
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Download LLaMA model from GCS (since it's already there)
RUN gcloud storage cp -r gs://pantrypilot-bucket/llama_base /app/models/

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
