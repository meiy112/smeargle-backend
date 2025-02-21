FROM golang:1.20 AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o app ./cmd/main.go

FROM python:3.9-slim
WORKDIR /app

# RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /app/app .

COPY --from=builder /app/internal/scripts ./internal/scripts

COPY --from=builder /app/images ./images

EXPOSE 8080

ENTRYPOINT ["./app"]