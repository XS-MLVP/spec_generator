MODULE ?= Sbuffer
CONFIG ?= DefaultConfig
VERSION ?= v2.0.1

.PHONY: init preflight rtl evidence render render-check validate lint clean-cache

init:
	git submodule update --init --recursive

preflight:
	./tools/preflight.sh --module "$(MODULE)" --config "$(CONFIG)" --strict --document-tools

rtl:
	./tools/generate_rtl.sh --module "$(MODULE)" --config "$(CONFIG)"

evidence:
	./tools/generate_rtl.sh --module "$(MODULE)" --config "$(CONFIG)" --version "$(VERSION)"

render:
	./tools/validate_mermaid.py --document "outputs/$(MODULE)/$(MODULE)_design_document_zh_$(VERSION).md" --output-dir "evidence/$(MODULE)/$(VERSION)/diagrams"

render-check:
	rm -rf ".cache/mermaid-check/$(MODULE)/$(VERSION)"
	./tools/validate_mermaid.py --document "outputs/$(MODULE)/$(MODULE)_design_document_zh_$(VERSION).md" --output-dir ".cache/mermaid-check/$(MODULE)/$(VERSION)"

validate:
	./tools/validate_document.py --module "$(MODULE)" --version "$(VERSION)" --strict-evidence

lint:
	bash -n tools/*.sh
	python3 -m py_compile tools/*.py
	$(MAKE) render-check MODULE="$(MODULE)" VERSION="$(VERSION)"
	./tools/validate_repository.py
	$(MAKE) validate MODULE="$(MODULE)" VERSION="$(VERSION)"

clean-cache:
	rm -rf .cache
