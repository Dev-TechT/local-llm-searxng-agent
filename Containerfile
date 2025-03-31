# Use the official SearxNG image as the base
FROM docker.io/searxng/searxng:latest

# Copy the pre-configured settings.yml from the host build context
# into the image at the location SearxNG expects.
# Assumes the settings.yml file is in a 'searxng_config' subdirectory
# relative to this Containerfile during the build.
COPY ./searxng_config/settings.yml /etc/searxng/settings.yml

# The base image already defines the correct CMD/ENTRYPOINT