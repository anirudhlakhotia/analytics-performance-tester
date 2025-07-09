FROM openjdk:17-jdk-slim

# Install yq for YAML parsing
RUN apt-get update && apt-get install -y \
    curl \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install yq
RUN curl -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o /usr/local/bin/yq \
    && chmod +x /usr/local/bin/yq

# Install Maven
RUN curl -fsSL https://archive.apache.org/dist/maven/maven-3/3.9.4/binaries/apache-maven-3.9.4-bin.tar.gz | tar xzf - -C /opt \
    && ln -s /opt/apache-maven-3.9.4 /opt/maven
ENV PATH="/opt/maven/bin:${PATH}"

WORKDIR /workspace

# Copy and install Python dependencies for dashboard
COPY analytics-performance-tester/analysis/requirements.txt /workspace/analysis/
RUN pip3 install -r analysis/requirements.txt

# Copy the analytics client and build it
COPY couchbase-analytics-jvm-clients /workspace/couchbase-analytics-jvm-clients
RUN cd /workspace/couchbase-analytics-jvm-clients && mvn clean install -DskipTests

# Copy project files
COPY analytics-performance-tester .

# Build Java application
RUN cd apps/java-analytics-client && mvn clean package -DskipTests

# Copy the decoupled runner script
COPY analytics-performance-tester/scripts/run-decoupled-benchmark.sh /workspace/

# Make scripts executable
RUN chmod +x scripts/*.sh
RUN chmod +x /workspace/run-decoupled-benchmark.sh

# Entry point that can handle both cluster modes
ENTRYPOINT ["/workspace/run-decoupled-benchmark.sh"]
