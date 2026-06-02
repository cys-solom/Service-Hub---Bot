// src/types/index.ts
// Shared TypeScript type definitions for the Service Hub MVP.
// Extend as needed during later phases.

/** Order status lifecycle */
export type OrderStatus =
  | "pending"
  | "paid"
  | "processing"
  | "delivered"
  | "failed"
  | "canceled"
  | "expired";

/** Payment status */
export type PaymentStatus = "pending" | "confirmed" | "failed" | "expired";

/** Product delivery mode */
export type DeliveryMode = "api" | "manual";

/** Non-secret settings keys allowed in the Setting table */
export const ALLOWED_SETTING_KEYS = [
  "store_name",
  "default_currency",
  "payment_timeout_minutes",
  "support_telegram_username",
  "support_whatsapp_url",
  "store_description",
  "announcement_text",
] as const;

export type SettingKey = (typeof ALLOWED_SETTING_KEYS)[number];
