# Initial Setup Commands for E-commerce KPI Dashboard SaaS

## 🚀 Quick Start Commands

Run these commands to create your new SaaS project:

```bash
# 1. Create new project directory
mkdir ecommerce-kpi-dashboard
cd ecommerce-kpi-dashboard

# 2. Initialize the project
npm init -y

# 3. Create project structure
mkdir -p frontend backend scheduler docs
mkdir -p backend/src/{routes,controllers,models,services,middleware,utils,database}
mkdir -p backend/src/services/{shopify,meta,printify}
mkdir -p frontend/src/{components,pages,hooks,utils,styles}
mkdir -p frontend/src/components/{Dashboard,Charts,Auth,Settings}
mkdir -p scheduler/src/{jobs,extractors,schedulers}

# 4. Initialize package.json files
cd frontend && npm init -y && cd ..
cd backend && npm init -y && cd ..
cd scheduler && npm init -y && cd ..
```

## 📦 Dependencies to Install

### Backend Dependencies
```bash
cd backend

# Core dependencies
npm install express cors helmet morgan dotenv
npm install prisma @prisma/client
npm install bcryptjs jsonwebtoken
npm install bull redis
npm install axios node-cron
npm install crypto-js

# Development dependencies  
npm install -D typescript @types/node @types/express
npm install -D @types/bcryptjs @types/jsonwebtoken
npm install -D nodemon ts-node
npm install -D prisma
```

### Frontend Dependencies
```bash
cd frontend

# Next.js setup
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Additional dependencies
npm install @radix-ui/react-icons
npm install @radix-ui/react-slot
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react
npm install recharts
npm install react-query @tanstack/react-query
npm install zustand
npm install next-auth
```

### Scheduler Dependencies
```bash
cd scheduler

# Core dependencies
npm install bull redis axios dotenv
npm install node-cron
npm install @prisma/client

# Development dependencies
npm install -D typescript @types/node nodemon ts-node
```

## 🗄️ Database Setup

### 1. Create .env files

**Backend .env:**
```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/kpi_dashboard"

# API Keys (encrypted in database)
JWT_SECRET="your-super-secret-jwt-key"
ENCRYPTION_KEY="your-32-char-encryption-key"

# External APIs
SHOPIFY_CLIENT_ID="your-shopify-app-client-id"
SHOPIFY_CLIENT_SECRET="your-shopify-app-client-secret"

# Redis
REDIS_URL="redis://localhost:6379"

# Environment
NODE_ENV="development"
PORT=3001
```

**Frontend .env.local:**
```env
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-nextauth-secret"
NEXT_PUBLIC_API_URL="http://localhost:3001"
```

### 2. Prisma Schema

Create `backend/prisma/schema.prisma`:
```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  password  String
  name      String?
  plan      String   @default("free") // free, pro, enterprise
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  stores Store[]
  
  @@map("users")
}

model Store {
  id            String   @id @default(cuid())
  userId        String
  name          String
  shopifyDomain String?
  status        String   @default("active") // active, paused, error
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  
  user         User           @relation(fields: [userId], references: [id], onDelete: Cascade)
  credentials  ApiCredential[]
  dailyKpis    DailyKpi[]
  
  @@map("stores")
}

model ApiCredential {
  id                String   @id @default(cuid())
  storeId          String
  provider         String   // shopify, meta, printify
  encryptedData    String   // encrypted API keys/tokens
  createdAt        DateTime @default(now())
  updatedAt        DateTime @updatedAt
  
  store Store @relation(fields: [storeId], references: [id], onDelete: Cascade)
  
  @@unique([storeId, provider])
  @@map("api_credentials")
}

model DailyKpi {
  id               String   @id @default(cuid())
  storeId         String
  date            DateTime @db.Date
  
  // Shopify Metrics
  shopifySales    Float?   @default(0)
  shopifyShipping Float?   @default(0)
  shopifyOrders   Int?     @default(0)
  shopifyAov      Float?   @default(0)
  newCustomers    Int?     @default(0)
  returningCustomers Int?  @default(0)
  
  // Meta Ads Metrics
  metaAdSpend     Float?   @default(0)
  metaImpressions Int?     @default(0)
  metaClicks      Int?     @default(0)
  metaCtr         Float?   @default(0)
  metaCpc         Float?   @default(0)
  metaRoas        Float?   @default(0)
  
  // Printify Metrics
  printifyCogs    Float?   @default(0)
  printifyOrders  Int?     @default(0)
  
  // Calculated Metrics
  grossProfit     Float?   @default(0)
  netProfit       Float?   @default(0)
  profitMargin    Float?   @default(0)
  
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  store Store @relation(fields: [storeId], references: [id], onDelete: Cascade)
  
  @@unique([storeId, date])
  @@map("daily_kpis")
}
```

## 🔧 Key Adaptation Points

### Reusing Your Existing Code

Your current extractors can be easily adapted:

**1. Shopify Extractor → Backend Service**
```typescript
// backend/src/services/shopify/ShopifyService.ts
// Adapt your existing shopify_extractor.py logic
```

**2. Meta Extractor → Backend Service**  
```typescript
// backend/src/services/meta/MetaService.ts
// Adapt your existing meta_extractor.py logic
```

**3. Printify Extractor → Backend Service**
```typescript
// backend/src/services/printify/PrintifyService.ts
// Adapt your FIXED printify_extractor.py logic (with quantity bug fixes!)
```

**4. Scheduling Logic → Background Jobs**
```typescript
// scheduler/src/jobs/DailyKpiJob.ts
// Adapt your daily_kpi_scheduler.py logic
```

## 🎯 Development Priority

1. **Week 1**: Backend API + Database setup
2. **Week 2**: Frontend dashboard + Auth
3. **Week 3**: Shopify integration
4. **Week 4**: Background jobs + scheduling
5. **Week 5**: Meta + Printify integrations
6. **Week 6**: Polish + deployment

## 📝 Next Actions

1. **Create the project** using the commands above
2. **Set up the database** with Prisma
3. **Build the basic API** endpoints
4. **Create the dashboard** UI
5. **Adapt your extractors** to the new architecture

Would you like me to help you create any specific files or start with a particular component?