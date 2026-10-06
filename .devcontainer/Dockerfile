# Image Python des dev containers, sans la source de paquets « yarn » qu'elle embarque : sa clé
# de signature n'est plus reconnue et fait échouer apt-get update, donc l'installation du
# bureau distant et de Chromium. IUC n'utilise pas yarn.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm
RUN grep -rl yarnpkg /etc/apt/sources.list.d/ | xargs -r rm -f
