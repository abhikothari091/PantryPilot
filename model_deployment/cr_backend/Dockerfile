FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

RUN apt-get update && apt-get install -y python3 python3-pip git curl apt-transport-https ca-certificates gnupg && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && apt-get install -y google-cloud-sdk && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD mkdir -p /app/models && \
    if gcloud storage ls gs://${GCS_BUCKET_NAME}/llama3b_lambda_lora >/dev/null 2>&1; then \
    gcloud storage cp -r gs://${GCS_BUCKET_NAME}/llama3b_lambda_lora /app/models/; \
    else \
    echo "WARNING: Model not found in GCS. Starting without pre-loaded model."; \
    mkdir -p /app/models/llama3b_lambda_lora; \
    fi && \
    uvicorn main:app --host 0.0.0.0 --port 7860