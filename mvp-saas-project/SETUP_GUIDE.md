# Setup Guide - E-commerce KPI Dashboard SaaS

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ installed
- PostgreSQL database
- Redis server
- Git

### 1. Project Initialization

```bash
# Copy this folder to your new workspace
cp -r mvp-saas-project/ /path/to/your/workspace/ecommerce-kpi-dashboard
cd /path/to/your/workspace/ecommerce-kpi-dashboard

# Initialize root package.json
npm init -y

# Create project structure
mkdir -p backend/src/{routes,controllers,models,services,middleware,utils,database}
mkdir -p backend/src/services/{shopify,meta,printify}
mkdir -p backend/prisma
mkdir -p frontend/src/{app,components,hooks,lib}
mkdir -p frontend/src/components/{dashboard,charts,auth,settings}
mkdir -p scheduler/src/{jobs,extractors,schedulers}
mkdir -p docs
```

### 2. Backend Setup

```bash
cd backend

# Initialize package.json
npm init -y

# Install dependencies
npm install express cors helmet morgan dotenv
npm install prisma @prisma/client
npm install bcryptjs jsonwebtoken
npm install bull redis ioredis
npm install axios node-cron
npm install crypto-js zod

# Development dependencies
npm install -D typescript @types/node @types/express
npm install -D @types/bcryptjs @types/jsonwebtoken
npm install -D @types/cors @types/morgan
npm install -D nodemon ts-node
npm install -D @types/bull

# Initialize TypeScript
npx tsc --init
```

### 3. Frontend Setup

```bash
cd ../frontend

# Create Next.js app
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Install additional dependencies
npm install @radix-ui/react-icons
npm install @radix-ui/react-slot
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react
npm install recharts
npm install @tanstack/react-query
npm install zustand
npm install next-auth
npm install axios
```

### 4. Scheduler Setup

```bash
cd ../scheduler

# Initialize package.json
npm init -y

# Install dependencies
npm install bull redis ioredis axios dotenv
npm install node-cron @prisma/client
npm install crypto-js

# Development dependencies
npm install -D typescript @types/node nodemon ts-node
npm install -D @types/bull

# Initialize TypeScript
npx tsc --init
```

## 🗄️ Database Setup

### 1. Environment Variables

Create `.env` files:

**Backend `.env`:**
```env
# Database
DATABASE_URL="postgresql://username:password@localhost:5432/kpi_dashboard"

# JWT & Encryption
JWT_SECRET="your-super-secret-jwt-key-min-32-chars"
ENCRYPTION_KEY="your-32-character-encryption-key-here"

# Redis
REDIS_URL="redis://localhost:6379"

# External APIs (for development)
SHOPIFY_CLIENT_ID="your-shopify-app-client-id"
SHOPIFY_CLIENT_SECRET="your-shopify-app-client-secret"

# Environment
NODE_ENV="development"
PORT=3001
```

**Frontend `.env.local`:**
```env
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-nextauth-secret-key"
NEXT_PUBLIC_API_URL="http://localhost:3001"
```

**Scheduler `.env`:**
```env
# Database (same as backend)
DATABASE_URL="postgresql://username:password@localhost:5432/kpi_dashboard"

# Redis (same as backend)
REDIS_URL="redis://localhost:6379"

# Environment
NODE_ENV="development"
```

### 2. Database Schema

Create `backend/prisma/schema.prisma` (see PROJECT_PLAN.md for full schema).

### 3. Database Migration

```bash
cd backend

# Generate Prisma client
npx prisma generate

# Create and run migrations
npx prisma migrate dev --name init

# (Optional) Seed database
npx prisma db seed
```

## 🔧 Initial Code Files

### Backend Entry Point

Create `backend/src/index.ts`:
```typescript
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';

import authRoutes from './routes/auth';
import storeRoutes from './routes/stores';
import kpiRoutes from './routes/kpis';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/stores', storeRoutes);
app.use('/api/kpis', kpiRoutes);

// Health check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
```

### Frontend Layout

Create `frontend/src/app/layout.tsx`:
```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'E-commerce KPI Dashboard',
  description: 'Automated KPI tracking for e-commerce businesses',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          {children}
        </div>
      </body>
    </html>
  );
}
```

### Scheduler Entry Point

Create `scheduler/src/index.ts`:
```typescript
import dotenv from 'dotenv';
import { Queue } from 'bull';
import cron from 'node-cron';

import { DailyKpiJob } from './jobs/DailyKpiJob';

dotenv.config();

const dailyKpiQueue = new Queue('daily-kpi', {
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
  },
});

// Process jobs
dailyKpiQueue.process(DailyKpiJob.process);

// Schedule daily job at 6 AM UTC
cron.schedule('0 6 * * *', async () => {
  console.log('🕕 Scheduling daily KPI collection...');
  await dailyKpiQueue.add('collect-daily-kpis', {
    date: new Date().toISOString().split('T')[0],
  });
});

console.log('📅 Scheduler started');
```

## 🏃‍♂️ Running the Application

### Development Mode

```bash
# Terminal 1: Backend
cd backend
npm run dev

# Terminal 2: Frontend  
cd frontend
npm run dev

# Terminal 3: Scheduler
cd scheduler
npm run dev

# Terminal 4: Redis (if not running as service)
redis-server

# Terminal 5: PostgreSQL (if not running as service)
pg_ctl -D /usr/local/var/postgres start
```

### Production Setup

```bash
# Build all applications
cd backend && npm run build
cd ../frontend && npm run build
cd ../scheduler && npm run build

# Start production servers
cd backend && npm start
cd ../frontend && npm start
cd ../scheduler && npm start
```

## 🔗 Service Integration

### Adapting Existing Extractors

Your current Python extractors can be adapted to TypeScript services:

1. **Shopify Extractor** → `backend/src/services/shopify/ShopifyService.ts`
2. **Meta Extractor** → `backend/src/services/meta/MetaService.ts`
3. **Printify Extractor** → `backend/src/services/printify/PrintifyService.ts`

See the `services/` folder for detailed implementations.

## 📝 Next Steps

1. **Set up the development environment** using the commands above
2. **Create the database schema** and run migrations
3. **Implement authentication** (register/login)
4. **Build the basic dashboard** UI
5. **Adapt the first extractor** (Shopify)
6. **Test with sample data**
7. **Add background job processing**
8. **Integrate remaining services** (Meta, Printify)

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error:**
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Ensure database exists

**Redis Connection Error:**
- Check Redis is running
- Verify REDIS_URL in .env
- Install Redis if not present

**Port Already in Use:**
- Change PORT in .env files
- Kill existing processes: `lsof -ti:3000 | xargs kill -9`

**Module Not Found:**
- Run `npm install` in all directories
- Check TypeScript configuration
- Verify import paths

## 📞 Support

If you encounter issues during setup:
1. Check the troubleshooting section above
2. Review the PROJECT_PLAN.md for technical details
3. Ensure all prerequisites are installed
4. Verify environment variables are correct

---

*This setup guide will get you from zero to a working development environment for the MVP SaaS platform.*