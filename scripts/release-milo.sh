#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--no-promote]" >&2
  exit 2
}

no_promote=false
case "${1:-}" in
  "") ;;
  --no-promote) no_promote=true ;;
  *) usage ;;
esac
[[ $# -le 1 ]] || usage

source_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
git -C "$source_root" fetch origin
commit="$(git -C "$source_root" rev-parse --verify 'refs/remotes/origin/main^{commit}')"
echo "Releasing origin/main at $commit"

cli="${PLOW_AGENTS_CLI:-plow-agents}"
cli="$(command -v "$cli")" || {
  echo "plow-agents not found; put it on PATH or set PLOW_AGENTS_CLI." >&2
  exit 1
}
[[ "$cli" == /* ]] || cli="$(cd "$(dirname "$cli")" && pwd -P)/$(basename "$cli")"
[[ -x "$cli" ]] || { echo "Plow CLI is not executable: $cli" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq is required." >&2; exit 1; }

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/milo-release.XXXXXXXX")"
temp_root="$(cd "$temp_root" && pwd -P)"
release_tree="$temp_root/source"
marker="$temp_root/.release-milo-owned"
: > "$marker"
cleanup() {
  status=$?
  trap - EXIT INT TERM
  if git -C "$source_root" worktree list --porcelain | grep -Fqx "worktree $release_tree"; then
    if ! git -C "$source_root" worktree remove --force "$release_tree"; then
      echo "Could not remove temporary worktree: $release_tree" >&2
      exit 1
    fi
  fi
  if [[ -f "$marker" && "$temp_root" == */milo-release.* ]]; then
    rm -rf -- "$temp_root"
  else
    echo "Temporary directory not recognized; preserved: $temp_root" >&2
    exit 1
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

git -C "$source_root" worktree add --detach "$release_tree" "$commit"
cd "$release_tree"
[[ "$(git rev-parse HEAD)" == "$commit" && -z "$(git status --porcelain --untracked-files=all)" ]] || {
  echo "Temporary worktree is not a clean checkout of origin/main." >&2
  exit 1
}

image="ghcr.io/lopesvini/desk-ai-employee:milo-$commit"
# Fast release smoke: default-off, test-to-real path, tamper refusal, uncertain send.
python3 -m unittest discover -s tests/envio -p 'test_*.py' -q \
  -k test_desligado_por_padrao \
  -k test_teste_depois_envio_real_pela_caixa_do_agente \
  -k test_texto_mudado_nao_sai \
  -k test_erro_do_servidor_vira_incerto_e_nao_reenvia
python3 -m unittest discover -s tests/rascunhos -p 'test_*.py' -q
python3 -m unittest discover -s tests/busca -p 'test_*.py' -q
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || {
  echo "Tests changed the release worktree; refusing to build." >&2
  exit 1
}

echo "Building $image for linux/amd64"
"$cli" image build "$image"

reference="$("$cli" image push "$image")"
[[ "$reference" =~ ^ghcr\.io/lopesvini/desk-ai-employee@sha256:[0-9a-f]{64}$ ]] || {
  echo "Plow CLI did not return an immutable digest reference." >&2
  exit 1
}
digest="${reference#*@}"
current="$("$cli" image show milo | jq -er '.plow.image')"

printf '\nCommit: %s\nImage: %s\nDigest: %s\nCurrently promoted: %s\nTo promote: %s\n' \
  "$commit" "$image" "$digest" "$current" "$reference"

if [[ "$current" == "$reference" ]]; then
  echo "This version is already promoted to Milo One Click Deploy."
  exit 0
fi

if "$no_promote"; then
  echo "Push complete; promotion skipped."
  exit 0
fi

read -r -p 'Promote this image to Milo One Click Deploy? [y/N] ' answer || answer=''
[[ "$answer" == y ]] || { echo "Promotion cancelled."; exit 0; }

"$cli" image promote milo "$reference"
promoted="$("$cli" image show milo | jq -er '.plow.image')"
[[ "$promoted" == "$reference" ]] || {
  printf 'Promotion verification failed: expected %s, Plow reports %s\n' "$reference" "$promoted" >&2
  exit 1
}
echo "Verified: Milo One Click Deploy points to $promoted"
