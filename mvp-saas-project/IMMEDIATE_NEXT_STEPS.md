# Immediate Next Steps for Claude Code

## 🚀 Start Here - First Commands to Run

When Claude Code reads this, execute these commands in order:

### 1. Read All Documentation First
```
Please read these files in this exact order:
1. CLAUDE_PROMPT.md (project context)
2. PROJECT_PLAN.md (technical specifications) 
3. SETUP_GUIDE.md (implementation steps)
4. backend-services.md (code implementations)
```

### 2. Initial Project Setup
```bash
# Install root dependencies
npm install

# Create folder structure
mkdir -p backend/src/{routes,controllers,models,services,middleware,utils,database}
mkdir -p backend/src/services/{shopify,meta,printify,shared}
mkdir -p backend/prisma
mkdir -p frontend/src/{app,components,hooks,lib}
mkdir -p frontend/src/components/{dashboard,charts,auth,settings}
mkdir -p scheduler/src/{jobs,extractors,schedulers}
mkdir -p docs

# Copy environment template
cp .env.example .env
```

### 3. Backend Setup Priority
```bash
cd backend
npm init -y
# Install all dependencies from SETUP_GUIDE.md
# Create Prisma schema from PROJECT_PLAN.md
# Implement services from backend-services.md
```

## 📋 Development Priority Order

### Phase 1: Foundation (Week 1)
- [ ] **Backend API structure** (Express + TypeScript)
- [ ] **Database schema** (Prisma + PostgreSQL)  
- [ ] **User authentication** (JWT + bcrypt)
- [ ] **Basic API endpoints** (/auth, /stores, /kpis)

### Phase 2: Core Features (Week 2)  
- [ ] **Shopify service** (adapt from backend-services.md)
- [ ] **Frontend dashboard** (Next.js + Tailwind)
- [ ] **Store connection flow** 
- [ ] **Basic KPI display**

### Phase 3: Integrations (Week 3)
- [ ] **Meta Ads service** 
- [ ] **Printify service** (with quantity bug fix!)
- [ ] **Background job system** (Bull + Redis)
- [ ] **Daily data collection**

### Phase 4: Polish (Week 4)
- [ ] **Advanced dashboard features**
- [ ] **Error handling & notifications**  
- [ ] **Multi-store support**
- [ ] **Basic billing system**

## 🔑 Critical Code Locations

### Most Important Files to Create:

1. **backend/prisma/schema.prisma** (from PROJECT_PLAN.md)
2. **backend/src/services/printify/PrintifyService.ts** (from backend-services.md - includes bug fix!)
3. **backend/src/services/shopify/ShopifyService.ts** (from backend-services.md)
4. **frontend/src/app/dashboard/page.tsx** (main dashboard)
5. **scheduler/src/jobs/DailyKpiJob.ts** (background processing)

## ⚠️ Don't Forget These Critical Elements

### **Printify Quantity Bug Fix**
```typescript
// CRITICAL: In PrintifyService.ts
// Don't multiply by quantity - API returns totals already!
const productCost = parseFloat(item.cost || '0') / 100; // Already includes quantity
const shippingCost = parseFloat(item.shipping_cost || '0') / 100; // Already includes quantity
totalCost += productCost + shippingCost; // NO quantity multiplication!
```

### **Database Schema Key Points**
- Multi-tenant design (users → stores → daily_kpis)
- Encrypted API credentials
- Proper indexing on date queries
- Support for multiple stores per user

### **Security Requirements**
- Encrypt all API credentials before storing
- Use JWT for authentication
- Validate all input data
- Rate limit API endpoints

## 📊 Expected File Structure After Setup

```
ecommerce-kpi-dashboard/
├── backend/
│   ├── src/
│   │   ├── index.ts
│   │   ├── routes/
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── shopify/ShopifyService.ts
│   │   │   ├── meta/MetaService.ts
│   │   │   ├── printify/PrintifyService.ts
│   │   │   └── shared/ApiCredentialService.ts
│   │   └── middleware/
│   ├── prisma/
│   │   └── schema.prisma
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── scheduler/
│   ├── src/
│   │   ├── index.ts
│   │   └── jobs/
│   └── package.json
└── package.json
```

## 🎯 Quick Validation Tests

After each phase, test these:

### Phase 1 Validation:
- [ ] Backend server starts on port 3001
- [ ] Database connection works
- [ ] User can register/login
- [ ] Basic API endpoints respond

### Phase 2 Validation:
- [ ] Frontend loads at localhost:3000
- [ ] User can connect Shopify store
- [ ] Basic dashboard shows test data
- [ ] Shopify API integration works

### Phase 3 Validation:
- [ ] All three services (Shopify, Meta, Printify) work
- [ ] Background jobs process correctly
- [ ] Daily KPI calculation is accurate
- [ ] **Printify COGS matches expected values**

## 💡 Pro Tips for Claude Code

1. **Use the provided TypeScript services** - they're already adapted from working Python code
2. **Follow the database schema exactly** - it's designed for multi-tenancy
3. **Implement Printify service first** - it has the most critical bug fix
4. **Test with sample data** before connecting real APIs
5. **Build incrementally** - get each phase working before moving to next

## 🚨 If You Get Stuck

1. **Re-read the relevant documentation section**
2. **Check the backend-services.md for code examples**
3. **Verify environment variables are set correctly**
4. **Test individual services before integrating**
5. **Ask specific questions about unclear requirements**

---

**Ready to start? Begin with Phase 1 and work through systematically. All the hard business logic is already figured out - now we just need to implement it as a beautiful SaaS product!**