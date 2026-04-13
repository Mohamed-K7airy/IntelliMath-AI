FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file (needs to copy the backend folder since it's inside backend/)
COPY backend/requirements.txt ./backend/

# Install the underlying dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the rest of the application
COPY . .

# Expose the necessary port
EXPOSE 8000

# Set environment variables commonly used in python
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Command to run the application (Uses os.environ.get('PORT') inside app.py)
CMD ["python", "backend/app.py"]
