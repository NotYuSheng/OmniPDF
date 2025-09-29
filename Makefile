# Makefile for Helm chart management in OmniPDF

# Default namespace and configurable chart
NAMESPACE ?= omnipdf
CHART_NAME ?= example-service
CHART_DIR ?= helm/$(CHART_NAME)
ENV ?= staging

# Service-specific values files (environment-specific only)
SERVICE_ENV_VALUES_FILE ?= $(CHART_DIR)/values-$(ENV).yaml
SERVICE_BASE_VALUES_FILE ?= $(CHART_DIR)/values.yaml

# Build values file list (prioritize environment-specific, fallback to base for rbac)
ifneq ($(wildcard $(SERVICE_ENV_VALUES_FILE)),)
    VALUES_FILES = -f $(SERVICE_ENV_VALUES_FILE)
else ifneq ($(wildcard $(SERVICE_BASE_VALUES_FILE)),)
    VALUES_FILES = -f $(SERVICE_BASE_VALUES_FILE)
else
    $(error No values file found for $(CHART_NAME). Expected: $(SERVICE_ENV_VALUES_FILE) or $(SERVICE_BASE_VALUES_FILE))
endif

# Default port for port-forwarding (override as needed)
LOCAL_PORT ?= 8000
REMOTE_PORT ?= 8000

.PHONY: help install install-all upgrade upgrade-all uninstall uninstall-all lint status port-forward

help:
	@echo "Makefile commands for Helm chart management:"
	@echo ""
	@echo "Single-service commands:"
	@echo "  make install                Install chart (CHART_NAME, ENV)"
	@echo "                              e.g. make install CHART_NAME=chat-service ENV=staging"
	@echo "  make upgrade                Upgrade chart (CHART_NAME, ENV)"
	@echo "                              e.g. make upgrade CHART_NAME=embedder-service ENV=prod"
	@echo "  make uninstall              Uninstall chart (CHART_NAME)"
	@echo "                              e.g. make uninstall CHART_NAME=pdf-processor"
	@echo "  make lint                   Run helm lint on chart (CHART_NAME)"
	@echo "                              e.g. make lint CHART_NAME=embedder-service"
	@echo "  make lint-all               Lint all charts under ./helm/"
	@echo "  make status                 Show status of Helm release (CHART_NAME)"
	@echo "                              e.g. make status CHART_NAME=chat-service"
	@echo "  make port-forward           Port-forward a pod to local machine"
	@echo "                              e.g. make port-forward CHART_NAME=chat-service LOCAL_PORT=8000 REMOTE_PORT=8000"
	@echo ""
	@echo "Multi-service commands:"
	@echo "  make install-all            Install all charts (ENV)"
	@echo "                              e.g. make install-all ENV=prod"
	@echo "  make upgrade-all            Upgrade all charts (ENV)"
	@echo "                              e.g. make upgrade-all ENV=staging"
	@echo "  make uninstall-all          Uninstall all charts under ./helm/"
	@echo ""
	@echo "Values System:"
	@echo "  Uses explicit environment-specific files only:"
	@echo "  1. helm/{SERVICE}/values-{ENV}.yaml         - Environment-specific configuration"
	@echo "  2. helm/{SERVICE}/values.yaml               - Fallback for rbac only"
	@echo ""
	@echo "Environment Variables:"
	@echo "  ENV                         Environment (staging, prestaging, prod) - defaults to 'staging'"
	@echo ""
	@echo "Development Environment:"
	@echo "  Use docker-compose for local development:"
	@echo "    docker-compose up -d                           # Start all services locally"
	@echo "    docker-compose logs -f chat_service            # View service logs"
	@echo ""
	@echo "⚠️ IMPORTANT:"
	@echo "  Avoid underscores (_) in CHART_NAME or release names."
	@echo "  Use hyphens (-) instead to follow Kubernetes naming conventions (RFC 1123)."
	@echo "  Example: use chat-service ✅, not chat_service ❌"

## Install a single Helm chart
install:
	@echo "Installing $(CHART_NAME) for environment: $(ENV)"
	@echo "Values files (in order): $(VALUES_FILES)"
	helm upgrade --install $(CHART_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		$(VALUES_FILES)

## Upgrade a single Helm chart
upgrade:
	@echo "Upgrading $(CHART_NAME) for environment: $(ENV)"
	@echo "Values files (in order): $(VALUES_FILES)"
	helm upgrade $(CHART_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) \
		$(VALUES_FILES)

## Uninstall a single Helm chart
uninstall:
	helm uninstall $(CHART_NAME) \
		--namespace $(NAMESPACE)

## Lint all Helm charts under ./helm/
lint-all:
	@echo "Linting all Helm charts under ./helm/..."
	@for dir in helm/*/; do \
		CHART=$$(basename $$dir); \
		if [ "$$CHART" != "shared-values" ] && [ "$$CHART" != "assets" ]; then \
			echo "Linting chart: $$CHART"; \
			helm lint $$dir || exit 1; \
		else \
			echo "Skipping non-chart directory: $$dir"; \
		fi; \
	done

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

# Helper function to deploy all charts (used by both install-all and upgrade-all)
define deploy-all-charts
	@echo "$(1) all Helm charts under ./helm/ for environment: $(ENV)"
	@for dir in helm/*/; do \
		CHART=$$(basename $$dir); \
		if [ "$$CHART" != "shared-values" ] && [ "$$CHART" != "assets" ]; then \
			echo "$(1) chart: $$CHART"; \
			if [ -f "helm/$$CHART/values-$(ENV).yaml" ]; then \
				CHART_VALUES="-f helm/$$CHART/values-$(ENV).yaml"; \
			elif [ -f "helm/$$CHART/values.yaml" ]; then \
				CHART_VALUES="-f helm/$$CHART/values.yaml"; \
			else \
				echo "Error: No values file found for $$CHART"; \
				exit 1; \
			fi; \
			helm upgrade --install $$CHART helm/$$CHART \
				--namespace $(NAMESPACE) \
				--create-namespace \
				$$CHART_VALUES; \
		fi; \
	done
endef

## Install all Helm charts in ./helm/
install-all:
	$(call deploy-all-charts,Installing)

## Upgrade all Helm charts in ./helm/
upgrade-all:
	$(call deploy-all-charts,Upgrading)

## Uninstall all Helm charts in ./helm/
uninstall-all:
	@echo "Uninstalling all Helm charts under ./helm/..."
	@for dir in helm/*/; do \
		CHART=$$(basename $$dir); \
		if [ "$$CHART" != "shared-values" ] && [ "$$CHART" != "assets" ]; then \
			echo "Uninstalling chart: $$CHART"; \
			helm uninstall $$CHART \
				--namespace $(NAMESPACE); \
		fi; \
	done

## Port-forward a running pod (default 8000:8000)
port-forward:
ifeq ($(CHART_NAME),example-service)
	@echo "ERROR: CHART_NAME must be specified. Example usage:"
	@echo "  make port-forward CHART_NAME=chat-service LOCAL_PORT=3000 REMOTE_PORT=8000"
	@exit 1
else
	kubectl --namespace $(NAMESPACE) port-forward \
	  deployment/$(CHART_NAME) \
	  $(LOCAL_PORT):$(REMOTE_PORT)
endif
