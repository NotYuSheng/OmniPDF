# Security Notes

## Known CVEs - Accepted Risk

### CVE-2025-47907 in minio/minio:RELEASE.2025-07-23T15-54-02Z and minio/mc:RELEASE.2025-07-21T05-28-08Z

**Status:** ACCEPTED RISK  
**Severity:** HIGH  
**Component:** Go stdlib v1.24.5 in MinIO server and client binaries

**Description:**  
Database/sql Postgres Scan Race Condition vulnerability in Go's standard library affects the compiled MinIO binaries.

**Impact Assessment:**  
- **Low Risk for OmniPDF**: MinIO is used for S3-compatible object storage, not PostgreSQL operations
- **No Database Usage**: Neither MinIO service nor mc client interact with PostgreSQL databases
- **Limited Attack Surface**: The vulnerable code path (database/sql Postgres scanning) is not exercised
- **Container Isolation**: MinIO runs in isolated Docker containers with limited network exposure

**Mitigation Options Considered:**
1. **Rebuild from source** - Complex, requires maintaining custom build pipeline
2. **Wait for upstream fix** - MinIO will release new version with Go 1.24.6+
3. **Accept risk** - ✅ **CHOSEN** - Minimal impact given our usage pattern

**Monitoring:**
- Check for MinIO releases compiled with Go 1.24.6+ monthly
- Re-evaluate if PostgreSQL integration is added to the stack

**Decision Date:** 2025-09-04  
**Next Review:** 2025-10-04  
**Decision By:** Development Team