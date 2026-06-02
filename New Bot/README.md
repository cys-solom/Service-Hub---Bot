# Service Hub — Digital Products Platform

Serverless digital products selling platform built with Next.js, Prisma, and Stripe.

## Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Database**: PostgreSQL (Neon Serverless)
- **ORM**: Prisma 7
- **Payments**: Stripe
- **Bot**: Telegram (grammY, webhook mode)
- **Deployment**: Vercel

## Setup

```bash
# 1. Install dependencies
npm install

# 2. Copy env template and fill in values
cp .env.example .env.local

# 3. Run database migrations
npm run db:migrate

# 4. Seed default data (admin user, default category, settings)
npm run db:seed

# 5. Start dev server
npm run dev
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production (generates Prisma client + Next.js build) |
| `npm run db:migrate` | Run Prisma migrations |
| `npm run db:seed` | Seed default admin, category, and settings |
| `npm run db:studio` | Open Prisma Studio (database GUI) |

## Environment Variables

See `.env.example` for the full list. All secrets (API keys, tokens, Stripe keys) are stored **only** in environment variables, never in the database.
