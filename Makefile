# Makefile for Helm chart management in OmniPDF

# Default namespace and configurable chart
NAMESPACE ?= omnipdf
CHART_NAME ?= example-service
CHART_DIR ?= helm/$(CHART_NAME)
VALUES_FILE ?= $(CHART_DIR)/values.yaml

# Default port for port-forwarding (override as needed)
LOCAL_PORT ?= 8000
REMOTE_PORT ?= 8000

.PHONY: help install install-all upgrade upgrade-all uninstall uninstall-all lint status port-forward

help:
	@echo "Makefile commands for Helm chart management:"
	@echo ""
	@echo "Single-service commands:"
	@echo "  make install                Install chart (CHART_NAME)"
	@echo "                              e.g. make install CHART_NAME=chat-service"
	@echo "  make upgrade                Upgrade chart (CHART_NAME)"
	@echo "                              e.g. make upgrade CHART_NAME=embedder-service"
	@echo "  make uninstall              Uninstall chart (CHART_NAME)"
	@echo "                              e.g. make uninstall CHART_NAME=pdf-processor"
	@echo "  make lint                   Run helm lint on chart (CHART_NAME)"
	@echo "                              e.g. make lint CHART_NAME=embedder-service"
	@echo "  make status                 Show status of Helm release (CHART_NAME)"
	@echo "                              e.g. make status CHART_NAME=chat-service"
	@echo "  make port-forward           Port-forward a pod to local machine"
	@echo "                              e.g. make port-forward CHART_NAME=chat-service LOCAL_PORT=8000 REMOTE_PORT=8000"
	@echo ""
	@echo "Multi-service commands:"
	@echo "  make install-all            Install all charts under ./helm/"
	@echo "  make upgrade-all            Upgrade all charts under ./helm/"
	@echo "  make uninstall-all          Uninstall all charts under ./helm/"
	@echo ""
	@echo "⚠️ IMPORTANT:"
	@echo "  Avoid underscores (_) in CHART_NAME or release names."
	@echo "  Use hyphens (-) instead to follow Kubernetes naming conventions (RFC 1123)."
	@echo "  Example: use chat-service ✅, not chat_service ❌"

## Install a single Helm chart
install:
	helm upgrade --install $(CHART_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--values $(VALUES_FILE)

## Upgrade a single Helm chart
upgrade:
	helm upgrade $(CHART_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) \
		--values $(VALUES_FILE)

## Uninstall a single Helm chart
uninstall:
	helm uninstall $(CHART_NAME) \
		--namespace $(NAMESPACE)

## Run lint check on a chart
lint:
	helm lint $(CHART_DIR)

## Show release status and pod info
status:
	@echo "=== Helm Release Status ==="
	helm status $(CHART_NAME) -n $(NAMESPACE)
	@echo ""
	@echo "=== Pod Status ==="
	kubectl get pods -n $(NAMESPACE) -l "app.kubernetes.io/name=$(CHART_NAME),app.kubernetes.io/instance=$(CHART_NAME)"

## Install all Helm charts in ./helm/
install-all:
	@echo "Installing all Helm charts under ./helm/..."
	@for dir in helm/*/; do \
		CHART=$$(basename $$dir); \
		echo "Installing chart: $$CHART"; \
		helm upgrade --install $$CHART helm/$$CHART \
			--namespace $(NAMESPACE) \
			--create-namespace \
			--values helm/$$CHART/values.yaml; \
	done

## Upgrade all Helm charts in ./helm/
upgrade-all:
	@echo "Upgrading all Helm charts under ./helm/..."
	@for dir in helm/*/; do \
		CHART=$$(basename $$dir); \
		echo "Upgrading chart: $$CHART"; \
		helm upgrade --install $$CHART helm/$$CHART \
			--namespace $(NAMESPACE) \
			--create-namespace \
			--values helm/$$CHART/values.yaml; \
	done

## Uninstall all Helm charts in ./helm/
uninstall-all:
	@echo "Uninstalling all Helm charts under ./helm/..."
	@for dir in helm/*/; do \
		CHART=$$(basename $$dir); \
		echo "Uninstalling chart: $$CHART"; \
		helm uninstall $$CHART \
			--namespace $(NAMESPACE); \
	done

## Port-forward a running pod (default 8000:8000)
port-forward:
ifeq ($(CHART_NAME),example-service)
	@echo "ERROR: CHART_NAME must be specified. Example usage:"
	@echo "  make port-forward CHART_NAME=chat-service LOCAL_PORT=3000 REMOTE_PORT=8000"
	@exit 1
else
	kubectl --namespace $(NAMESPACE) port-forward \
	  $$(kubectl get pod -n $(NAMESPACE) -l "app.kubernetes.io/name=$(CHART_NAME),app.kubernetes.io/instance=$(CHART_NAME)" -o jsonpath="{.items[0].metadata.name}") \
	  $(LOCAL_PORT):$(REMOTE_PORT)
endif
