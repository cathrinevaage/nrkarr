FROM alpine:3.20

RUN apk add --no-cache python3 py3-pip \
 && pip install --break-system-packages --no-cache-dir \
      "flask>=3.0" "pyyaml>=6.0"

WORKDIR /app
COPY nrkarr ./nrkarr

ENV NRKARR_CONFIG=/config/config.yml
VOLUME /config
EXPOSE 9121

HEALTHCHECK --interval=60s --timeout=5s \
  CMD wget -qO- http://127.0.0.1:9121/health || exit 1

CMD ["python3", "-m", "nrkarr"]
