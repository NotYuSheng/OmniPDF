# Helm Assets

This directory contains shared assets used across Helm charts.

## Files

- `logo.svg` - WebWork company logo used in Chart.yaml icon fields
  - **Format**: SVG (112KB)
  - **Usage**: Referenced in Chart.yaml as GitHub raw URL
  - **Company**: WebWork logo for consistent branding across all services

## Usage in Charts

Reference the logo in your Chart.yaml files:

```yaml
# Chart.yaml
icon: file://logo.svg
```

## Logo Guidelines

- ✅ **Current logo**: 112KB SVG with transparent background
- ✅ **Works on**: Light and dark backgrounds
- ✅ **Scalable**: Vector format works at any size
- ✅ **Branding**: Consistent WebWork identity across all services