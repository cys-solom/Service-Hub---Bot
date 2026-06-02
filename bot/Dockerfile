FROM python:3.12-slim

WORKDIR /app

# Install bot dependencies
COPY bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot/ .

# Copy shared backend modules (models, core) that the bot imports
COPY backend/models/ /app/models/
COPY backend/core/ /app/core/

CMD ["python", "main.py"]
