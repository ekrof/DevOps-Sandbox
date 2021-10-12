#!/bin/bash
set -e
set -o pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit
fi

. tool-versions.env

echo Installing kustomize v$KUSTOMIZE
curl -sL https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv${KUSTOMIZE}/kustomize_v${KUSTOMIZE}_linux_amd64.tar.gz | \
tar xz && mv kustomize /usr/local/bin/kustomize

echo Installing yq v$YQ
curl -sL https://github.com/mikefarah/yq/releases/download/v${YQ}/yq_linux_amd64.tar.gz |\
tar xz && mv yq_linux_amd64 /usr/local/bin/yq
