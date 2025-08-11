# Helm Assets

This directory contains shared assets used across Helm charts.

## Files

- `logo.svg` - Webwork company logo used in Chart.yaml icon fields
  - **Format**: SVG (112KB)
  - **Usage**: Referenced in Chart.yaml as GitHub raw URL
  - **Company**: Webwork logo for consistent branding across all services

## Usage in Charts

Reference the logo in your Chart.yaml files:

```yaml
# Chart.yaml
icon: https://github.com/YOUR-ORG/omnipdf/raw/main/helm/assets/logo.svg
```

**Note**: Replace `YOUR-ORG` with your actual GitHub organization/username.

## Logo Guidelines

- ✅ **Current logo**: 112KB SVG with transparent background
- ✅ **Works on**: Light and dark backgrounds
- ✅ **Scalable**: Vector format works at any size
- ✅ **Branding**: Consistent Webwork identity across all services