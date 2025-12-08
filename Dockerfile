FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python + pip
RUN apt-get update && apt-get install -y python3 python3-pip git && apt-get clean

# Make python command available (pip already exists)
RUN ln -sf /usr/bin/python3 /usr/bin/python

COPY model_deployment/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY model_deployment/backend/main.py model_deployment/backend/model_service.py model_deployment/backend/database.py model_deployment/backend/models.py ./
COPY model_development/models ./models

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
