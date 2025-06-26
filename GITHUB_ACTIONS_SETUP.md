# GitHub Actions Setup Guide

This guide will help you set up automated daily KPI collection using GitHub Actions.

## 🚀 Quick Setup Steps

### 1. Configure Repository Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add the following secrets (exact names required):

#### Notion Secrets
- `NOTION_TOKEN` - Your Notion integration token
- `NOTION_DAILY_KPIS_DB` - Your Notion Daily KPIs database ID

#### Shopify Secrets  
- `SHOPIFY_SHOP_URL` - Your shop URL (e.g., `your-shop.myshopify.com`)
- `SHOPIFY_ACCESS_TOKEN` - Your Shopify API access token

#### Meta Ads Secrets (for Daily KPIs only)
- `META_ACCESS_TOKEN` - Your Meta Ads API access token
- `META_AD_ACCOUNT_ID` - Your Meta ad account ID (with `act_` prefix)

#### Printify Secrets (for Daily KPIs only)
- `PRINTIFY_API_TOKEN` - Your Printify API token
- `PRINTIFY_SHOP_ID` - Your Printify shop ID

### 2. How the Automation Works

#### Three Automated Workflows

**Daily KPI Collection:**
- **Schedule**: Every day at 9:00 AM UTC (11:00 AM CET)
- **Purpose**: High-level business metrics (revenue, orders, ad spend, etc.)
- **Database**: Daily KPIs database
- **Data Sources**: Shopify + Meta Ads + Printify

**Orders Analytics Collection:**
- **Schedule**: Every day at 9:30 AM UTC (11:30 AM CET) - 30 minutes later
- **Purpose**: Detailed order-level analytics (customer info, geography, etc.)
- **Database**: Orders Analytics database  
- **Data Sources**: Shopify only

**Financial Analytics Collection:**
- **Schedule**: Every day at 10:00 AM UTC (12:00 PM CET) - 1 hour later
- **Purpose**: Transaction-level financial data (fees, payments, profitability)
- **Database**: Financial Analytics database
- **Data Sources**: Shopify only

#### Manual Runs
- Go to **Actions** tab → Choose the workflow → **Run workflow**
- Optional: Specify a custom date (YYYY-MM-DD format)
- Useful for testing or collecting missed days

### 3. Monitoring & Troubleshooting

#### Check Run Status
1. Go to **Actions** tab in your repository
2. Click on **Daily KPI Collection** workflow
3. View individual run details and logs

#### Common Issues & Solutions

**❌ "Secrets not found" error**
- Verify all secret names match exactly (case-sensitive)
- Check that all required secrets are added

**❌ "API authentication failed"**
- Verify API tokens are still valid
- Check if any API credentials have expired

**❌ "No data found" error**  
- Normal for days with no business activity
- Check if the date/timezone is correct

**❌ "Notion database not found"**
- Verify the Notion integration has access to your database
- Check that `NOTION_DAILY_KPIS_DB` is the correct database ID

#### Success Indicators
- ✅ Green checkmark in Actions tab
- ✅ New entry appears in your Notion database
- ✅ Log shows "Daily KPI collection completed successfully"

### 4. Customizing the Schedule

To change when the automation runs, edit `.github/workflows/daily-kpi-collection.yml`:

```yaml
schedule:
  - cron: '0 9 * * *'  # 9:00 AM UTC daily
```

**Common schedules:**
- `'0 8 * * *'` - 8:00 AM UTC (10:00 AM CET)
- `'0 10 * * *'` - 10:00 AM UTC (12:00 PM CET)  
- `'0 9 * * 1-5'` - 9:00 AM UTC, weekdays only

**Cron format:** `minute hour day month day-of-week`

### 5. Testing Your Setup

#### Test Manual Run
1. Go to **Actions** → **Daily KPI Collection** → **Run workflow**
2. Leave date field empty (uses yesterday)
3. Click **Run workflow**
4. Check logs for success/failure

#### Test Specific Date
1. Use manual run with a specific date (e.g., `2025-06-25`)
2. Verify data appears correctly in Notion
3. Check all metrics are populated

### 6. Cost Considerations

- **GitHub Actions**: 2,000 free minutes/month for public repos
- **Daily runs**: ~2-3 minutes each = ~60-90 minutes/month
- **Well within free tier** for most users

### 7. Security Best Practices

✅ **DO:**
- Use repository secrets for all API tokens
- Regularly rotate API tokens
- Monitor workflow runs for failures

❌ **DON'T:**
- Never commit API tokens to code
- Don't share secret values in issues/comments
- Don't use personal access tokens for production

## 🎉 You're All Set!

Once configured, your KPIs will be automatically collected every day and populated in your Notion database. The system is designed to be reliable, secure, and maintenance-free.

For any issues, check the Actions logs or create an issue in this repository.