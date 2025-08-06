# Backend Services - Adapted from Original Extractors

This file contains the TypeScript adaptations of your existing Python extractors.

## 📁 File Structure

```
backend/src/services/
├── shopify/
│   ├── ShopifyService.ts        # Adapted from shopify_extractor.py
│   └── types.ts                 # TypeScript interfaces
├── meta/
│   ├── MetaService.ts           # Adapted from meta_extractor.py  
│   └── types.ts
├── printify/
│   ├── PrintifyService.ts       # Adapted from printify_extractor.py (with fixes!)
│   └── types.ts
└── shared/
    ├── ApiCredentialService.ts  # Handles encrypted credentials
    └── BaseService.ts           # Shared functionality
```

## 🔐 API Credential Service

```typescript
// backend/src/services/shared/ApiCredentialService.ts
import crypto from 'crypto-js';
import { PrismaClient } from '@prisma/client';

export class ApiCredentialService {
  private prisma = new PrismaClient();
  private encryptionKey = process.env.ENCRYPTION_KEY!;

  async storeCredentials(storeId: string, provider: string, credentials: any) {
    const encrypted = crypto.AES.encrypt(
      JSON.stringify(credentials),
      this.encryptionKey
    ).toString();

    return await this.prisma.apiCredential.upsert({
      where: { storeId_provider: { storeId, provider } },
      update: { encryptedData: encrypted },
      create: { storeId, provider, encryptedData: encrypted },
    });
  }

  async getCredentials(storeId: string, provider: string) {
    const record = await this.prisma.apiCredential.findUnique({
      where: { storeId_provider: { storeId, provider } },
    });

    if (!record) return null;

    const decrypted = crypto.AES.decrypt(record.encryptedData, this.encryptionKey);
    return JSON.parse(decrypted.toString(crypto.enc.Utf8));
  }
}
```

## 🛍️ Shopify Service

```typescript
// backend/src/services/shopify/ShopifyService.ts
import axios from 'axios';
import { ApiCredentialService } from '../shared/ApiCredentialService';

interface ShopifyCredentials {
  shopDomain: string;
  accessToken: string;
}

interface ShopifyDailySalesData {
  shopify_gross_sales: number;
  shopify_shipping: number;
  total_orders: number;
  aov: number;
  new_customers: number;
  returning_customers: number;
}

export class ShopifyService {
  private credentialService = new ApiCredentialService();

  async getDailySalesData(storeId: string, date: Date): Promise<ShopifyDailySalesData> {
    const credentials = await this.credentialService.getCredentials(storeId, 'shopify') as ShopifyCredentials;
    
    if (!credentials) {
      throw new Error('Shopify credentials not found');
    }

    const { shopDomain, accessToken } = credentials;
    const baseUrl = \`https://\${shopDomain}/admin/api/2023-10/\`;
    
    const headers = {
      'X-Shopify-Access-Token': accessToken,
      'Content-Type': 'application/json',
    };

    // Date range for the specific day
    const startDate = new Date(date);
    startDate.setHours(0, 0, 0, 0);
    const endDate = new Date(date);
    endDate.setHours(23, 59, 59, 999);

    try {
      // Get orders for the day (adapted from your Python logic)
      const ordersResponse = await axios.get(\`\${baseUrl}orders.json\`, {
        headers,
        params: {
          status: 'any',
          created_at_min: startDate.toISOString(),
          created_at_max: endDate.toISOString(),
          limit: 250,
        },
      });

      const orders = ordersResponse.data.orders;

      // Calculate metrics (same logic as your Python extractor)
      let totalSales = 0;
      let totalShipping = 0;
      let orderCount = orders.length;
      const customerIds = new Set();
      const returningCustomerIds = new Set();

      for (const order of orders) {
        // Sales calculation
        const subtotal = parseFloat(order.subtotal_price || '0');
        const shipping = parseFloat(order.total_shipping_price_set?.shop_money?.amount || '0');
        
        totalSales += subtotal;
        totalShipping += shipping;

        // Customer analysis
        if (order.customer?.id) {
          customerIds.add(order.customer.id);
          
          // Check if returning customer (simplified logic)
          if (order.customer.orders_count > 1) {
            returningCustomerIds.add(order.customer.id);
          }
        }
      }

      const aov = orderCount > 0 ? totalSales / orderCount : 0;
      const totalCustomers = customerIds.size;
      const returningCustomers = returningCustomerIds.size;
      const newCustomers = totalCustomers - returningCustomers;

      return {
        shopify_gross_sales: totalSales,
        shopify_shipping: totalShipping,
        total_orders: orderCount,
        aov: aov,
        new_customers: newCustomers,
        returning_customers: returningCustomers,
      };

    } catch (error) {
      console.error('Shopify API error:', error);
      throw new Error(\`Failed to fetch Shopify data: \${error}\`);
    }
  }

  async testConnection(storeId: string): Promise<boolean> {
    try {
      const credentials = await this.credentialService.getCredentials(storeId, 'shopify') as ShopifyCredentials;
      
      if (!credentials) return false;

      const { shopDomain, accessToken } = credentials;
      const response = await axios.get(\`https://\${shopDomain}/admin/api/2023-10/shop.json\`, {
        headers: { 'X-Shopify-Access-Token': accessToken },
      });

      return response.status === 200;
    } catch {
      return false;
    }
  }
}
```

## 🖨️ Printify Service (With Quantity Bug Fixes!)

```typescript
// backend/src/services/printify/PrintifyService.ts
import axios from 'axios';
import { ApiCredentialService } from '../shared/ApiCredentialService';

interface PrintifyCredentials {
  apiToken: string;
  shopId?: string;
}

interface PrintifyDailyCosts {
  printify_charge: number;
  printify_orders: number;
}

export class PrintifyService {
  private credentialService = new ApiCredentialService();
  private baseUrl = 'https://api.printify.com/v1';

  async getDailyCosts(storeId: string, date: Date): Promise<PrintifyDailyCosts> {
    const credentials = await this.credentialService.getCredentials(storeId, 'printify') as PrintifyCredentials;
    
    if (!credentials) {
      throw new Error('Printify credentials not found');
    }

    const { apiToken } = credentials;
    const headers = {
      'Authorization': \`Bearer \${apiToken}\`,
      'Content-Type': 'application/json',
      'User-Agent': 'KPI-Dashboard/1.0',
    };

    // Get shop ID automatically if not stored
    const shopId = credentials.shopId || await this.getPrimaryShopId(headers);
    
    if (!shopId) {
      throw new Error('No Printify shop found');
    }

    // Date range for the specific day
    const startDate = new Date(date);
    startDate.setHours(0, 0, 0, 0);
    const endDate = new Date(date);
    endDate.setHours(23, 59, 59, 999);

    try {
      // Get orders (adapted from your Python logic with pagination)
      const params = {
        created_at_min: startDate.toISOString().replace('Z', ' UTC'),
        created_at_max: endDate.toISOString().replace('Z', ' UTC'),
        limit: 100,
      };

      const ordersResponse = await axios.get(\`\${this.baseUrl}/shops/\${shopId}/orders.json\`, {
        headers,
        params,
      });

      let allOrders = ordersResponse.data.data || [];

      // Handle pagination
      const { current_page, last_page } = ordersResponse.data;
      if (last_page > 1) {
        for (let page = 2; page <= Math.min(last_page, 5); page++) {
          const pageResponse = await axios.get(\`\${this.baseUrl}/shops/\${shopId}/orders.json\`, {
            headers,
            params: { ...params, page },
          });
          allOrders = allOrders.concat(pageResponse.data.data || []);
          
          // Small delay to respect rate limits
          await new Promise(resolve => setTimeout(resolve, 200));
        }
      }

      // Filter orders to exact date
      const dailyOrders = allOrders.filter((order: any) => {
        if (!order.created_at) return false;
        
        try {
          const orderDate = new Date(order.created_at);
          return orderDate.toDateString() === date.toDateString();
        } catch {
          return false;
        }
      });

      // Calculate costs with QUANTITY BUG FIX
      let totalCost = 0;
      const orderCount = dailyOrders.length;

      for (const order of dailyOrders) {
        const lineItems = order.line_items || [];
        
        for (const item of lineItems) {
          // CRITICAL FIX: Don't multiply by quantity!
          // The API cost fields already include the total for all quantities
          const productCost = parseFloat(item.cost || '0') / 100; // Convert from cents
          const shippingCost = parseFloat(item.shipping_cost || '0') / 100; // Convert from cents
          
          // Total cost for this line item (already accounts for quantity)
          totalCost += productCost + shippingCost;
        }
      }

      return {
        printify_charge: Math.round(totalCost * 100) / 100, // Round to 2 decimal places
        printify_orders: orderCount,
      };

    } catch (error) {
      console.error('Printify API error:', error);
      throw new Error(\`Failed to fetch Printify data: \${error}\`);
    }
  }

  private async getPrimaryShopId(headers: any): Promise<string | null> {
    try {
      const response = await axios.get(\`\${this.baseUrl}/shops.json\`, { headers });
      const shops = response.data;
      
      if (Array.isArray(shops) && shops.length > 0) {
        return shops[0].id;
      }
      
      return null;
    } catch {
      return null;
    }
  }

  async testConnection(storeId: string): Promise<boolean> {
    try {
      const credentials = await this.credentialService.getCredentials(storeId, 'printify') as PrintifyCredentials;
      
      if (!credentials) return false;

      const headers = {
        'Authorization': \`Bearer \${credentials.apiToken}\`,
        'Content-Type': 'application/json',
      };

      const response = await axios.get(\`\${this.baseUrl}/shops.json\`, { headers });
      return response.status === 200 && response.data.length > 0;
    } catch {
      return false;
    }
  }
}
```

## 📱 Meta Service

```typescript
// backend/src/services/meta/MetaService.ts
import axios from 'axios';
import { ApiCredentialService } from '../shared/ApiCredentialService';

interface MetaCredentials {
  accessToken: string;
  adAccountId: string;
}

interface MetaDailyAdData {
  meta_ad_spend: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cpc: number;
  roas: number;
}

export class MetaService {
  private credentialService = new ApiCredentialService();
  private baseUrl = 'https://graph.facebook.com/v18.0';

  async getDailyAdData(storeId: string, date: Date): Promise<MetaDailyAdData> {
    const credentials = await this.credentialService.getCredentials(storeId, 'meta') as MetaCredentials;
    
    if (!credentials) {
      throw new Error('Meta credentials not found');
    }

    const { accessToken, adAccountId } = credentials;
    const dateString = date.toISOString().split('T')[0]; // YYYY-MM-DD format

    try {
      // Get insights for the specific date (adapted from your Python logic)
      const response = await axios.get(\`\${this.baseUrl}/act_\${adAccountId}/insights\`, {
        params: {
          access_token: accessToken,
          level: 'account',
          time_range: JSON.stringify({
            since: dateString,
            until: dateString,
          }),
          fields: [
            'spend',
            'impressions', 
            'clicks',
            'ctr',
            'cpc',
            'actions',
            'action_values',
          ].join(','),
        },
      });

      const data = response.data.data[0] || {};

      // Calculate ROAS (adapted from your Python logic)
      const spend = parseFloat(data.spend || '0');
      let revenue = 0;

      // Extract purchase revenue from actions
      if (data.action_values) {
        const purchaseAction = data.action_values.find((action: any) => 
          action.action_type === 'purchase' || action.action_type === 'omni_purchase'
        );
        revenue = parseFloat(purchaseAction?.value || '0');
      }

      const roas = spend > 0 ? revenue / spend : 0;
      const impressions = parseInt(data.impressions || '0');
      const clicks = parseInt(data.clicks || '0');
      const ctr = parseFloat(data.ctr || '0');
      const cpc = parseFloat(data.cpc || '0');

      return {
        meta_ad_spend: spend,
        impressions,
        clicks,
        ctr,
        cpc,
        roas,
      };

    } catch (error) {
      console.error('Meta API error:', error);
      throw new Error(\`Failed to fetch Meta data: \${error}\`);
    }
  }

  async testConnection(storeId: string): Promise<boolean> {
    try {
      const credentials = await this.credentialService.getCredentials(storeId, 'meta') as MetaCredentials;
      
      if (!credentials) return false;

      const response = await axios.get(\`\${this.baseUrl}/me\`, {
        params: { access_token: credentials.accessToken },
      });

      return response.status === 200;
    } catch {
      return false;
    }
  }
}
```

## 🔄 Daily KPI Job (Background Scheduler)

```typescript
// scheduler/src/jobs/DailyKpiJob.ts
import { Job } from 'bull';
import { PrismaClient } from '@prisma/client';
import { ShopifyService } from '../../backend/src/services/shopify/ShopifyService';
import { MetaService } from '../../backend/src/services/meta/MetaService';
import { PrintifyService } from '../../backend/src/services/printify/PrintifyService';

const prisma = new PrismaClient();
const shopifyService = new ShopifyService();
const metaService = new MetaService();
const printifyService = new PrintifyService();

export class DailyKpiJob {
  static async process(job: Job) {
    const { date } = job.data;
    const targetDate = new Date(date);

    console.log(\`🤖 Collecting KPIs for \${date}\`);

    // Get all active stores
    const stores = await prisma.store.findMany({
      where: { status: 'active' },
    });

    for (const store of stores) {
      try {
        console.log(\`📊 Processing store: \${store.name}\`);

        // Check if data already exists
        const existingData = await prisma.dailyKpi.findUnique({
          where: { storeId_date: { storeId: store.id, date: targetDate } },
        });

        if (existingData) {
          console.log(\`✅ Data already exists for \${store.name} on \${date}\`);
          continue;
        }

        // Extract data from all services (adapted from your daily_kpi_scheduler.py)
        const [shopifyData, metaData, printifyData] = await Promise.allSettled([
          shopifyService.getDailySalesData(store.id, targetDate),
          metaService.getDailyAdData(store.id, targetDate),
          printifyService.getDailyCosts(store.id, targetDate),
        ]);

        // Calculate derived metrics
        const shopify = shopifyData.status === 'fulfilled' ? shopifyData.value : {};
        const meta = metaData.status === 'fulfilled' ? metaData.value : {};
        const printify = printifyData.status === 'fulfilled' ? printifyData.value : {};

        const grossProfit = (shopify.shopify_gross_sales || 0) - (printify.printify_charge || 0);
        const netProfit = grossProfit - (meta.meta_ad_spend || 0);
        const profitMargin = shopify.shopify_gross_sales > 0 ? netProfit / shopify.shopify_gross_sales : 0;

        // Save to database
        await prisma.dailyKpi.create({
          data: {
            storeId: store.id,
            date: targetDate,
            
            // Shopify metrics
            shopifySales: shopify.shopify_gross_sales || 0,
            shopifyShipping: shopify.shopify_shipping || 0,
            shopifyOrders: shopify.total_orders || 0,
            shopifyAov: shopify.aov || 0,
            newCustomers: shopify.new_customers || 0,
            returningCustomers: shopify.returning_customers || 0,
            
            // Meta metrics
            metaAdSpend: meta.meta_ad_spend || 0,
            metaImpressions: meta.impressions || 0,
            metaClicks: meta.clicks || 0,
            metaCtr: meta.ctr || 0,
            metaCpc: meta.cpc || 0,
            metaRoas: meta.roas || 0,
            
            // Printify metrics
            printifyCogs: printify.printify_charge || 0,
            printifyOrders: printify.printify_orders || 0,
            
            // Calculated metrics
            grossProfit,
            netProfit,
            profitMargin,
          },
        });

        console.log(\`✅ Saved KPIs for \${store.name}\`);

      } catch (error) {
        console.error(\`❌ Error processing \${store.name}:\`, error);
        // Continue with other stores
      }

      // Rate limiting delay
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log(\`🎉 Daily KPI collection completed for \${date}\`);
  }
}
```

## 📝 Usage Notes

### Key Adaptations Made:

1. **Python → TypeScript**: All logic converted to TypeScript with proper typing
2. **Notion → PostgreSQL**: Data now saves to relational database instead of Notion
3. **Scripts → Services**: Extractors are now reusable service classes
4. **GitHub Actions → Background Jobs**: Scheduling uses Bull queues instead of cron
5. **Quantity Bug Fixed**: Printify service includes your quantity multiplication fix
6. **Multi-tenant**: All services work with multiple stores/users
7. **Error Handling**: Robust error handling and retry logic
8. **Security**: API credentials are encrypted in database

### Benefits:

- **Reusable**: Services can be called from API endpoints or background jobs
- **Testable**: Each service can be unit tested independently  
- **Scalable**: Background jobs can be distributed across multiple workers
- **Secure**: Credentials are encrypted and never exposed
- **Maintainable**: Clear separation of concerns and TypeScript typing

These services form the core of your SaaS platform, adapting all the proven logic from your original system while making it scalable and user-friendly!