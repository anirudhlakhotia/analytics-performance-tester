# Makefile for Go Analytics Client

.PHONY: build clean test run

# Build the application
build:
	go build -o bin/go-analytics-client .

# Clean build artifacts
clean:
	rm -rf bin/

# Run tests
test:
	go test -v ./...

# Run the application (requires environment variables to be set)
run:
	go run .

# Install dependencies
deps:
	go mod tidy
	go mod download

# Format code
fmt:
	go fmt ./...

# Lint code (requires golangci-lint)
lint:
	golangci-lint run 