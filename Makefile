MODULE ?= Sbuffer
CONFIG ?= DefaultConfig
VERSION ?= v2.0.1
ALLOW_HISTORICAL_TEMPLATE ?=
CHANGE_TYPE ?=
SUMMARY ?=

.PHONY: init preflight rtl evidence render render-check validate metadata repo-lint template-check lint clean-cache

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
	./tools/validate_document.py --module "$(MODULE)" --version "$(VERSION)" --strict-evidence $(ALLOW_HISTORICAL_TEMPLATE)

metadata:
	python3 tools/update_document_metadata.py --module "$(MODULE)" --version "$(VERSION)" --update-history $(if $(CHANGE_TYPE),--change-type "$(CHANGE_TYPE)") $(if $(SUMMARY),--summary "$(SUMMARY)")

repo-lint:
	bash -n tools/*.sh
	python3 -m py_compile tools/*.py
	./tools/validate_repository.py

template-check:
	rm -rf ".cache/mermaid-check/template"
	./tools/validate_mermaid.py --document "templates/chip-design-document/chip_design_document_template_zh.md" --output-dir ".cache/mermaid-check/template"

lint:
	$(MAKE) repo-lint
	$(MAKE) render-check MODULE="$(MODULE)" VERSION="$(VERSION)"
	$(MAKE) validate MODULE="$(MODULE)" VERSION="$(VERSION)"

clean-cache:
	rm -rf .cache
