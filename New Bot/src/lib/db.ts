// src/lib/db.ts
// Prisma client singleton for serverless environments.
//
// Prisma 7 with Neon Serverless: Uses @prisma/adapter-neon with the
// HTTP-based adapter (PrismaNeonHttp) for optimal serverless performance.
//
// The client is created lazily on first access via the `db` getter to
// avoid errors during Next.js build (where DATABASE_URL may not be set).

import { PrismaClient } from "@prisma/client";
import { PrismaNeonHttp } from "@prisma/adapter-neon";

function createPrismaClient(): PrismaClient {
  const connectionString = process.env.DATABASE_URL;

  if (!connectionString) {
    throw new Error("DATABASE_URL environment variable is not set");
  }

  const adapter = new PrismaNeonHttp(connectionString, {
    arrayMode: false,
    fullResults: true,
  });

  return new PrismaClient({
    adapter,
    log:
      process.env.NODE_ENV === "development" ? ["warn", "error"] : ["error"],
  });
}

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

/** Lazily-initialized Prisma client. Safe to import at module scope. */
export function getDb(): PrismaClient {
  if (!globalForPrisma.prisma) {
    globalForPrisma.prisma = createPrismaClient();
  }
  return globalForPrisma.prisma;
}
