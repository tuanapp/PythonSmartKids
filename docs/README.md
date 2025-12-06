# SmartBoy Backend Documentation

*Last Updated: December 2025*

This folder contains all project documentation organized for easy navigation and maintenance.

## 📚 Documentation Index

| Document | Description | Audience |
|----------|-------------|----------|
| **[DATABASE.md](DATABASE.md)** | Database setup, schema, migrations | Developers, DevOps |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Vercel deployment & production setup | DevOps, Developers |
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Local environment setup & workflow | Developers |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System design & code organization | All team members |
| **[API_REFERENCE.md](API_REFERENCE.md)** | API endpoints & usage | Frontend devs, Integrators |
| **[USER_BLOCKING.md](USER_BLOCKING.md)** | User blocking feature documentation | Admins, Developers |
| **[TESTING.md](TESTING.md)** | Test organization & running tests | Developers |

## 🚀 Quick Start

### Local Development
```powershell
cd Backend_Python
.\start-dev.ps1
```
Server runs at: http://localhost:8000

### Production
```bash
# Deploy to Vercel (auto on push)
git push origin main

# Apply migrations
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
```

## 🔗 Key Links

- **Production API**: https://python-smart-kids.vercel.app
- **API Docs (Swagger)**: http://localhost:8000/docs (local) 
- **Database**: Neon PostgreSQL (cloud)
- **Deployment**: Vercel

## 📁 Related Documentation

| Location | Purpose |
|----------|---------|
| [`../README.md`](../README.md) | Main project README |
| [`../tests/README.md`](../tests/README.md) | Test suite documentation |
| [`../tests/TEST_SUITE_DOCUMENTATION.md`](../tests/TEST_SUITE_DOCUMENTATION.md) | Detailed test documentation |

## 📋 Documentation Guidelines

When updating documentation:

1. **Keep docs current** - Update when code changes
2. **Use clear naming** - Follow existing conventions
3. **Link appropriately** - Cross-reference related docs
4. **Include examples** - Show actual usage with code snippets

---

*See individual documentation files for detailed information.*
