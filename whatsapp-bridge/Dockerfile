FROM golang:1.26-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=1 go build -trimpath -ldflags="-s -w" -o /out/whatsapp-bridge .

FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --home-dir /data bridge \
    && install -d -m 0700 -o bridge -g bridge /data/store /data/outbox \
    && chmod 0700 /data
COPY --from=build /out/whatsapp-bridge /usr/local/bin/whatsapp-bridge
USER bridge
WORKDIR /data
ENV BRIDGE_HOST=0.0.0.0 \
    WHATSAPP_MEDIA_DIR=/data/outbox
EXPOSE 8080
ENTRYPOINT ["whatsapp-bridge"]
