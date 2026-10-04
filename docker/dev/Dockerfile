# Sprint local development image (used by ../../docker-compose.yml).
#
# The bench itself lives in a volume (created on first start by entrypoint.sh);
# this image only adds the entrypoint and a fingerprint of the app sources.
# `docker compose up --build` re-computes the fingerprint; when it changed, the
# container refreshes deps, rebuilds the frontend and runs `bench migrate`.

# --- fingerprint of everything that can require a build or a migration ------
FROM busybox:1.37 AS fingerprint
COPY pyproject.toml /src/pyproject.toml
COPY sprint /src/sprint
COPY frontend /src/frontend
RUN cd /src \
	&& find . -type f ! -path './sprint/public/frontend/*' ! -path './sprint/www/sprint.html' \
		-print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1 > /build-id

# --- dev image ---------------------------------------------------------------
FROM docker.io/frappe/bench:latest

COPY --chmod=755 docker/dev/entrypoint.sh /usr/local/bin/sprint-dev-entrypoint
USER root
# Tolerate CRLF checkouts on Windows; pre-create the mount points owned by frappe
# so the named volumes (copied up from the image on first use) are writable.
RUN sed -i 's/\r$//' /usr/local/bin/sprint-dev-entrypoint \
	&& mkdir -p /workspace/development/frappe-bench/apps/sprint/frontend/node_modules \
	&& chown -R frappe:frappe /workspace
USER frappe

COPY --from=fingerprint /build-id /opt/sprint-build-id

WORKDIR /workspace/development
ENTRYPOINT ["sprint-dev-entrypoint"]
