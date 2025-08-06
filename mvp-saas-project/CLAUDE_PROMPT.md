# Claude Code Prompt for SaaS MVP Development

## 🎯 Project Context & Goal

I have a working Python-based KPI tracking system for e-commerce (Shopify + Meta Ads + Printify) that successfully extracts daily metrics and stores them in Notion databases. The system works great but requires technical knowledge to set up and use.

**GOAL**: Transform this proven system into a user-friendly SaaS web application that non-technical e-commerce store owners can easily use.

## 📊 What the Original System Does

The current Python system:
- ✅ Extracts daily sales data from Shopify API
- ✅ Pulls Meta Ads performance metrics  
- ✅ Gets Printify COGS data (with important quantity bug fixes)
- ✅ Calculates profit margins and KPIs
- ✅ Stores everything in Notion databases
- ✅ Runs automated daily via GitHub Actions

**Key Achievement**: We discovered and fixed a critical Printify API bug where quantity multiplication was incorrectly applied, leading to inflated COGS calculations.

## 🚀 SaaS MVP Requirements

### Target Users
- Shopify store owners using Printify for print-on-demand
- E-commerce consultants managing multiple clients
- Marketing agencies running Meta Ads campaigns

### Core Features Needed
1. **Web Dashboard**: Replace Notion with native web interface
2. **Multi-tenant**: Support multiple users and stores
3. **Automated Data Collection**: Background jobs instead of GitHub Actions
4. **API Integrations**: Shopify, Meta Ads, Printify (reuse existing logic)
5. **User Authentication**: Secure login and store management
6. **Billing System**: Subscription-based pricing tiers

### Tech Stack Decision
- **Frontend**: Next.js + TypeScript + Tailwind CSS
- **Backend**: Node.js + Express + TypeScript  
- **Database**: PostgreSQL + Prisma ORM (instead of Notion)
- **Queue System**: Bull + Redis for background jobs
- **Hosting**: Vercel (frontend) + Railway (backend)

## 📋 What's Been Prepared

This workspace contains complete documentation and code templates:

### 1. **PROJECT_PLAN.md** 
- Complete technical specifications
- Database schema design
- UI/UX wireframes
- Business model and pricing
- Development timeline

### 2. **SETUP_GUIDE.md**
- Step-by-step setup instructions
- All dependencies and commands
- Environment configuration
- Development workflow

### 3. **backend-services.md**
- Complete TypeScript services adapted from the working Python extractors
- **CRITICAL**: Includes the Printify quantity bug fix
- API credential encryption
- Background job implementations

### 4. **package.json**
- All dependencies specified
- Development and build scripts
- Workspace configuration

## 🔧 Your Task

**Please help me build this SaaS MVP by:**

1. **Reading all documentation** to understand the full scope and requirements
2. **Setting up the development environment** following SETUP_GUIDE.md  
3. **Creating the database schema** using the Prisma configuration
4. **Implementing the backend API** using the provided TypeScript services
5. **Building the frontend dashboard** based on UI specifications
6. **Setting up background jobs** for automated data collection
7. **Testing integrations** with sample data

## ⚠️ Critical Requirements

### **Must Preserve from Original System:**
- ✅ **Printify quantity bug fix**: The fixed logic that doesn't multiply costs by quantity
- ✅ **Proven data extraction patterns**: The working API calls and data processing
- ✅ **Error handling**: Robust error handling for API failures
- ✅ **Rate limiting**: Proper delays between API calls

### **Must Implement for SaaS:**
- 🔐 **Security**: Encrypted API credentials, secure authentication
- 🏢 **Multi-tenancy**: Multiple users, multiple stores per user
- 📊 **Native dashboard**: Beautiful web interface (no Notion dependency)
- 💰 **Billing**: Subscription management (can be basic initially)
- 🔄 **Background processing**: Reliable daily data collection

## 🎯 Success Criteria

The MVP is successful when:
- ✅ A user can register and connect their Shopify store
- ✅ The system automatically collects daily KPIs (Shopify + Meta + Printify)
- ✅ Data is displayed in a beautiful web dashboard
- ✅ Multi-store support works correctly
- ✅ Background jobs run reliably
- ✅ The Printify COGS calculations are accurate (using our bug fix)

## 📖 How to Proceed

1. **Start by reading PROJECT_PLAN.md** for complete technical details
2. **Review SETUP_GUIDE.md** for implementation steps  
3. **Study backend-services.md** for the adapted TypeScript code
4. **Ask questions** if anything is unclear about the requirements
5. **Begin with backend setup** (database + API) then move to frontend

## 🎨 UI/UX Vision

Think "modern SaaS dashboard" like:
- Clean, professional design
- Real-time KPI cards showing revenue, orders, ROAS, profit
- Interactive charts for trends
- Easy store connection flow
- Mobile-responsive design

## 💡 Context About Original Success

This isn't a theoretical project - the Python version has been running successfully for months, processing real e-commerce data and providing valuable insights. We know the business logic works; we just need to package it as a user-friendly SaaS product.

The Printify quantity bug fix alone saved significant money on COGS calculations, proving the value of this system.

---

**Ready to build a profitable SaaS product together! Let's start by reviewing the documentation and setting up the development environment.**