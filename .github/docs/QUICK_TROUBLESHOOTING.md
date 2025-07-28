# Quick Troubleshooting Guide

## 🚨 Emergency Quick Fixes

### Build Failing with "Matrix vector 'arch' does not contain any values"

**Immediate Fix:**
```bash
# Check which strategy was used
gh run view --log | grep "Strategy used"

# If using hardcoded fallback, verify config.yaml:
cd aicleaner_v3
yq eval '.arch' config.yaml

# Quick fix - ensure architectures are defined:
yq eval '.arch = ["aarch64","amd64","armhf","armv7"]' -i config.yaml
```

### Pre-build Validation Failing

**Quick Diagnosis:**
```bash
# Check config.yaml syntax
cd aicleaner_v3
yamllint config.yaml

# Validate required fields
yq eval '.name, .version, .slug, .arch' config.yaml

# Fix missing fields
yq eval '.name = "AICleaner V3"' -i config.yaml
yq eval '.version = "1.1.0"' -i config.yaml
yq eval '.slug = "aicleaner_v3"' -i config.yaml
```

### Docker Build Failing

**Quick Checks:**
```bash
# Check Dockerfile syntax
cd aicleaner_v3
hadolint Dockerfile

# Test base image availability
docker manifest inspect ghcr.io/home-assistant/amd64-base:3.19

# Clean Docker environment
docker system prune -af
```

### Registry Push Failures

**Immediate Actions:**
```bash
# Check GitHub Container Registry permissions
gh auth status

# Re-authenticate if needed
gh auth login

# Manual push test
docker tag test-image ghcr.io/sporebattyl/aicleaner_v3:test
docker push ghcr.io/sporebattyl/aicleaner_v3:test
```

## 🔍 Quick Diagnostics

### Check Build Health
```bash
# Run health monitor
./.github/scripts/build-status-monitor.sh -l 5

# Check latest workflow run
gh run list --limit 1

# View specific run logs
gh run view <run-id> --log
```

### Validate Configuration
```bash
# Complete config validation
cd aicleaner_v3
echo "=== Config Validation ==="
echo "Name: $(yq eval '.name' config.yaml)"
echo "Version: $(yq eval '.version' config.yaml)"
echo "Slug: $(yq eval '.slug' config.yaml)"
echo "Architectures: $(yq eval '.arch[]' config.yaml | tr '\n' ' ')"
echo "Architecture count: $(yq eval '.arch | length' config.yaml)"
```

### Test Architecture Detection
```bash
cd aicleaner_v3

# Test Strategy 2 (Direct parsing)
echo "Testing direct config parsing..."
PARSED_ARCH=$(yq eval -o=json '.arch' config.yaml)
echo "Result: $PARSED_ARCH"
echo "Count: $(echo "$PARSED_ARCH" | jq '. | length')"

# Test Strategy 3 (Hardcoded fallback)
echo "Testing hardcoded fallback..."
HARDCODED_ARCH='["aarch64","amd64","armhf","armv7"]'
echo "Result: $HARDCODED_ARCH"
echo "Valid JSON: $(echo "$HARDCODED_ARCH" | jq -e . >/dev/null && echo "Yes" || echo "No")"
```

## ⚡ Emergency Recovery

### Rollback to Working State
```bash
# Find last successful build
gh run list --status success --limit 1

# Get the commit hash
WORKING_COMMIT=$(gh run list --status success --limit 1 --json headSha --jq '.[0].headSha')

# Revert to working state
git revert --no-edit HEAD..$WORKING_COMMIT
```

### Manual Emergency Build
```bash
cd aicleaner_v3

# Single architecture emergency build
docker buildx build \
  --platform linux/amd64 \
  --tag ghcr.io/sporebattyl/aicleaner_v3:emergency-$(date +%Y%m%d) \
  --push \
  .

echo "Emergency image: ghcr.io/sporebattyl/aicleaner_v3:emergency-$(date +%Y%m%d)"
```

### Reset Workflow State
```bash
# Cancel running workflows
gh run list --status in_progress --json databaseId --jq '.[].databaseId' | \
  xargs -I {} gh run cancel {}

# Clean up caches (if you have admin access)
gh api repos/:owner/:repo/actions/caches --method DELETE
```

## 📋 Quick Checklists

### Before Making Changes
- [ ] Run health check: `./.github/scripts/build-status-monitor.sh`
- [ ] Validate config: `yamllint aicleaner_v3/config.yaml`
- [ ] Check workflow syntax: `yamllint .github/workflows/build.yml`
- [ ] Test locally: `docker build aicleaner_v3/`

### After Changes
- [ ] Monitor first build closely
- [ ] Check all architectures complete
- [ ] Verify published images
- [ ] Update documentation if needed

### Weekly Maintenance
- [ ] Check build success rate (should be >90%)
- [ ] Review build duration trends
- [ ] Update base image versions if needed
- [ ] Clean up old artifacts

## 🆘 When All Else Fails

### Contact Information
- **Primary:** GitHub Issues in this repository
- **Emergency:** Direct maintainer contact
- **Documentation:** `.github/docs/BUILD_SYSTEM_GUIDE.md`

### Emergency Contacts
```bash
# Create emergency issue
gh issue create \
  --title "URGENT: Build System Failure" \
  --body "Quick description of issue and impact" \
  --label "priority:critical,type:bug"
```

### Last Resort Procedures
1. **Disable Automatic Builds:** Comment out cron triggers
2. **Switch to Manual Builds:** Use `workflow_dispatch` only
3. **Fallback to Previous Version:** Revert major changes
4. **External Build:** Use alternative CI/CD platform

---

**Remember:** This guide covers 90% of common issues. For complex problems, refer to the complete [Build System Guide](BUILD_SYSTEM_GUIDE.md).

**Emergency Principle:** Fix first, investigate later. Get builds working, then understand root cause.