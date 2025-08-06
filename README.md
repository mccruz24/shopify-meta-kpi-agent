# Shopify Meta KPI Agent

Automated analytics collection system for Shopify, Meta Ads, and Printify data with Notion integration.

## 📁 Repository Structure

```
shopify-meta-kpi-agent-1/
├── schedulers/                    # All scheduler scripts
│   ├── daily_kpi_scheduler.py     # Daily KPI collection
│   ├── financial_analytics_scheduler.py  # Financial analytics (payouts)
│   ├── orders_analytics_scheduler.py     # Orders analytics
│   ├── traffic_analytics_scheduler.py    # Traffic analytics
│   ├── printify_analytics_scheduler.py   # Printify analytics
│   └── daily_platform_metrics_transformer.py  # Platform metrics transform
├── src/                          # Core source code
│   ├── extractors/               # Data extraction modules
│   │   ├── shopify_extractor.py  # Shopify KPI data
│   │   ├── meta_extractor.py     # Meta ads data
│   │   ├── graphql_financial_analytics_extractor.py  # Financial payouts (GraphQL)
│   │   ├── orders_analytics_extractor.py  # Orders data
│   │   ├── traffic_analytics_extractor.py  # Traffic data
│   │   └── printify_analytics_extractor.py  # Printify data
│   ├── loaders/                  # Notion data loaders
│   │   ├── graphql_payout_notion_loader.py  # Financial data loader
│   │   ├── orders_notion_loader.py  # Orders data loader
│   │   ├── printify_notion_loader.py  # Printify data loader
│   │   └── traffic_notion_loader.py  # Traffic data loader
│   └── utils/                    # Utility functions
├── traffic_analytics_sync.py     # Traffic analytics sync logic
├── printify_analytics_sync.py    # Printify analytics sync logic
├── .github/                      # GitHub Actions workflows
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚀 Automated Workflows

The system runs automatically via GitHub Actions:

- **Daily KPI Collection**: Collects Shopify sales, Meta ads, and Printify costs
- **Financial Analytics**: Collects Shopify payout data using GraphQL
- **Orders Analytics**: Detailed order-level analytics
- **Traffic Analytics**: Store traffic and conversion data
- **Printify Analytics**: Cost of goods and order management
- **Platform Metrics**: Transforms data to platform-specific metrics

## 🔧 Setup

1. Set up environment variables in GitHub Secrets
2. Configure Notion database IDs
3. Set up API credentials for Shopify, Meta, and Printify

## 📊 Data Flow

1. **Extractors** pull data from APIs (Shopify, Meta, Printify)
2. **Loaders** store data in Notion databases
3. **Schedulers** orchestrate the daily collection process
4. **GitHub Actions** run the workflows automatically

## 🎯 Key Features

- **GraphQL Integration**: Uses Shopify GraphQL API for accurate payout data
- **Automated Scheduling**: Runs daily via GitHub Actions
- **Notion Integration**: Stores all data in organized Notion databases
- **Error Handling**: Comprehensive error handling and retry logic
- **Data Validation**: Ensures data quality and consistency
- **Clean Architecture**: Only essential production code included

## 📈 Analytics Coverage

- **Shopify**: Sales, orders, customers, payouts
- **Meta Ads**: Ad spend, impressions, clicks, ROAS
- **Printify**: Cost of goods, order management
- **Traffic**: Store visits, conversions, sources
- **Financial**: Payout analytics with detailed fee breakdowns
