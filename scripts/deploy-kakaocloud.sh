#!/usr/bin/env bash
# 카카오클라우드 KCR 푸시 + K8s 배포 스크립트
# 사용 전 아래 변수를 본인 환경에 맞게 수정하세요.

set -euo pipefail

# ===== 설정 (필수) =====
PROJECT_NAME="${PROJECT_NAME:-}"          # 예: my-project
CR_REPO_NAME="${CR_REPO_NAME:-}"          # 예: mcp-repo
ACCESS_KEY_ID="${ACCESS_KEY_ID:-}"
ACCESS_SECRET_KEY="${ACCESS_SECRET_KEY:-}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-./kubeconfig.yaml}"

if [[ -z "$PROJECT_NAME" || -z "$CR_REPO_NAME" ]]; then
  echo "PROJECT_NAME, CR_REPO_NAME 환경변수를 설정하세요."
  echo "예: PROJECT_NAME=my-project CR_REPO_NAME=mcp-repo ./scripts/deploy-kakaocloud.sh push"
  exit 1
fi

CR_URL="${PROJECT_NAME}.kr-central-2.kcr.dev"
IMAGE="${CR_URL}/${CR_REPO_NAME}/gift-mate-mcp:latest"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cmd="${1:-help}"

build() {
  echo "==> Docker build (linux/amd64)"
  docker build --platform linux/amd64 -t gift-mate-mcp:latest "$ROOT"
}

login() {
  if [[ -z "$ACCESS_KEY_ID" || -z "$ACCESS_SECRET_KEY" ]]; then
    echo "ACCESS_KEY_ID, ACCESS_SECRET_KEY 환경변수를 설정하세요."
    exit 1
  fi
  echo "==> KCR login"
  docker login "$CR_URL" --username "$ACCESS_KEY_ID" --password "$ACCESS_SECRET_KEY"
}

push() {
  build
  login
  echo "==> Tag & push"
  docker tag gift-mate-mcp:latest "$IMAGE"
  docker push "$IMAGE"
  echo "Pushed: $IMAGE"
}

secret() {
  if [[ -z "$ACCESS_KEY_ID" || -z "$ACCESS_SECRET_KEY" ]]; then
    echo "ACCESS_KEY_ID, ACCESS_SECRET_KEY 환경변수를 설정하세요."
    exit 1
  fi
  export KUBECONFIG="$KUBECONFIG_PATH"
  kubectl delete secret kc-cr-secret --ignore-not-found
  kubectl create secret docker-registry kc-cr-secret \
    --docker-server="$CR_URL" \
    --docker-username="$ACCESS_KEY_ID" \
    --docker-password="$ACCESS_SECRET_KEY"
}

deploy() {
  export KUBECONFIG="$KUBECONFIG_PATH"
  echo "==> Deploy to Kubernetes"
  sed "s|REPLACE_WITH_KCR_IMAGE|$IMAGE|g" "$ROOT/k8s/deployment.yaml" | kubectl apply -f -
  kubectl apply -f "$ROOT/k8s/service.yaml"
  kubectl rollout status deployment/gift-mate-mcp
  echo ""
  echo "Service EXTERNAL-IP 확인:"
  kubectl get service gift-mate-mcp-service
  echo ""
  echo "퍼블릭 IP 연결: 카카오클라우드 콘솔 > Load Balancing > gift-mate-mcp-service"
  echo "PlayMCP Endpoint: http://{PUBLIC_IP}/mcp"
}

case "$cmd" in
  build) build ;;
  login) login ;;
  push) push ;;
  secret) secret ;;
  deploy) deploy ;;
  all) push && secret && deploy ;;
  *)
    cat <<EOF
Usage:
  PROJECT_NAME=... CR_REPO_NAME=... ACCESS_KEY_ID=... ACCESS_SECRET_KEY=... \\
    ./scripts/deploy-kakaocloud.sh [build|login|push|secret|deploy|all]

  KUBECONFIG_PATH=./kubeconfig.yaml (기본값)

가이드: https://docs.kakaocloud.com/tutorial/container/k8s-engine-mcp
EOF
    ;;
esac
