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

CMD gcloud storage cp -r gs://pantrypilot-bucket/llama_base /app/models/ && \
    gcloud storage cp -r gs://pantrypilot-bucket/llama3b_lambda_lora /app/models/ && \
    uvicorn main:app --host 0.0.0.0 --port 7860