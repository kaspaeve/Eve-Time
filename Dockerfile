# Use an official Python runtime as the base image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Make port 80 available to the world outside this container (Optional if you don't have any port bindings)
EXPOSE 80

# Define environment variable (Optional)
# ENV NAME=World

# Run your_script_name.py when the container launches
CMD ["python", "your_bot_script_name.py"]
