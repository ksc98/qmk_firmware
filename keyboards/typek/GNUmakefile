# TypeK utility targets — run from this directory (keyboards/typek/).
# These are NOT part of the QMK build (firmware is built from the repo root with
# `make typek:via`, which uses rules.mk / keyboard.json, never this file).

PY := python3

.PHONY: help show-layers save-layers

help:
	@echo "TypeK utilities:"
	@echo "  make show-layers   print ASCII diagrams of every VIA keymap layer"
	@echo "  make save-layers   (re)generate layout-diagrams.md"

show-layers:
	@$(PY) tools/render_keymap.py

save-layers:
	@{ echo '# TypeK keymap layers'; \
	   echo; \
	   echo 'Auto-generated from `keymaps/via/keymap.c` by `make save-layers`. Do not edit by hand.'; \
	   echo; \
	   echo '```text'; \
	   $(PY) tools/render_keymap.py; \
	   echo '```'; \
	 } > layout-diagrams.md && echo "wrote $(CURDIR)/layout-diagrams.md"
