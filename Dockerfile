ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY services.yaml ./
COPY run.sh .
RUN chmod a+x run.sh

# Copy the www directory for Lovelace cards
COPY www/ /app/www/

# Start the application
CMD [ "./run.sh" ]

