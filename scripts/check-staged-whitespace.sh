#!/usr/bin/env sh
# Pre-commit whitespace gate: `git diff --check` over staged changes, excluding
# carried content that keeps its upstream formatting (extensions/toolkit course
# assets and third-party plugin snapshots; see the vendor lint exclusion for
# the same policy). Pathspec magic needs quoting that lefthook's sh -c strips,
# so the command lives here.
set -e
exec git diff --cached --check -- . \
  ':(exclude)extensions/bigbear-toolkit/**' \
  ':(exclude)extensions/third-party/**'
