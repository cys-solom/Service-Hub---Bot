// prisma/prisma.config.ts
// Prisma 7 configuration — connection URLs managed here instead of schema.prisma

import path from "node:path";
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: path.join(__dirname, "schema.prisma"),

  datasource: {
    url: process.env.DIRECT_DATABASE_URL ?? process.env.DATABASE_URL,
  },
});
