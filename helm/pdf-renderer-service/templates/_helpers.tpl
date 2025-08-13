{{/*
Expand the name of the chart.
*/}}
{{- define "pdf-renderer-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "pdf-renderer-service.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "pdf-renderer-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "pdf-renderer-service.labels" -}}
helm.sh/chart: {{ include "pdf-renderer-service.chart" . }}
{{ include "pdf-renderer-service.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "pdf-renderer-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pdf-renderer-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "pdf-renderer-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "pdf-renderer-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use
*/}}
{{- define "pdf-renderer-service.secretName" -}}
{{- if .Values.secrets.create }}
{{- include "pdf-renderer-service.fullname" . }}-secrets
{{- else }}
{{- .Values.secrets.name }}
{{- end }}
{{- end }}
