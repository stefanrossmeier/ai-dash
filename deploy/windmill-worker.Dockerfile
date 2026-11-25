# The prebuilt CE base has separate terms, including modification/wrapping
# restrictions. This build template is not image redistribution clearance.
# See THIRD_PARTY_NOTICES.md and docs/PUBLICATION.md before releasing an image.
ARG WM_IMAGE=ghcr.io/windmill-labs/windmill:1.775.1
FROM ${WM_IMAGE}
USER root
ENV AI_DASH_HOME=/opt/ai-dash
WORKDIR /opt/ai-dash
COPY pyproject.toml uv.lock README.md .python-version ./
COPY src ./src
COPY config ./config
COPY assets ./assets
RUN uv sync --frozen --no-dev --python 3.12
WORKDIR /tmp
