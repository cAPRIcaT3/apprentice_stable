# Use the official Python image
FROM python:3.10

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Run the GitHub Action script when the container starts
CMD ["python", "src/commenter.py"]
