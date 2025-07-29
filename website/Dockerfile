# 1. Use a lightweight Python 3.10 base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy all your app files into the container
COPY Homepage/ .

COPY requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Set environment variable to tell Flask not to buffer output (for better logging)
ENV PYTHONUNBUFFERED True

# 6. Expose port 8080, which Cloud Run expects
EXPOSE 8080

# 7. Start the app with Gunicorn (recommended for production)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]

#TESTING 
#CMD ["python", "app.py"]