// prisma/seed.ts
// Seeds the database with a default admin user and a default category.
// Run with: npx prisma db seed

import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  // ─── Default Admin ─────────────────────────────────
  const adminUsername = process.env.ADMIN_USERNAME || "admin";
  const adminPassword = process.env.ADMIN_PASSWORD || "changeme";

  const existingAdmin = await prisma.admin.findUnique({
    where: { username: adminUsername },
  });

  if (!existingAdmin) {
    const passwordHash = await bcrypt.hash(adminPassword, 12);
    await prisma.admin.create({
      data: {
        username: adminUsername,
        passwordHash,
      },
    });
    console.log(`✅ Admin user created: ${adminUsername}`);
  } else {
    console.log(`ℹ️  Admin user already exists: ${adminUsername}`);
  }

  // ─── Default Category ──────────────────────────────
  const existingCategory = await prisma.category.findUnique({
    where: { slug: "general" },
  });

  if (!existingCategory) {
    await prisma.category.create({
      data: {
        name: "General",
        slug: "general",
        description: "Default product category",
        sortOrder: 0,
        isVisible: true,
      },
    });
    console.log("✅ Default category created: General");
  } else {
    console.log("ℹ️  Default category already exists: General");
  }

  // ─── Default Settings ──────────────────────────────
  const defaults: Record<string, string> = {
    store_name: "Service Hub",
    default_currency: "USD",
    payment_timeout_minutes: "30",
    support_telegram_username: "",
    support_whatsapp_url: "",
    store_description: "Digital products platform",
  };

  for (const [key, value] of Object.entries(defaults)) {
    const existing = await prisma.setting.findUnique({ where: { key } });
    if (!existing) {
      await prisma.setting.create({ data: { key, value } });
      console.log(`✅ Setting created: ${key}`);
    }
  }

  console.log("\n🎉 Seed completed.");
}

main()
  .catch((e) => {
    console.error("❌ Seed failed:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
