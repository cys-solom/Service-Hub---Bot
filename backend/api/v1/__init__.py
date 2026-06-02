"""API v1 — Main router aggregating all sub-routers"""
from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.dashboard import router as dashboard_router
from api.v1.categories import router as categories_router
from api.v1.products import router as products_router
from api.v1.stock import router as stock_router
from api.v1.orders import router as orders_router
from api.v1.payments import router as payments_router
from api.v1.users import router as users_router
from api.v1.wallets import router as wallets_router
from api.v1.commands import router as commands_router
from api.v1.messages import router as messages_router
from api.v1.buttons import router as buttons_router
from api.v1.coupons import router as coupons_router
from api.v1.referrals import router as referrals_router
from api.v1.support import router as support_router
from api.v1.settings import router as settings_router
from api.v1.audit import router as audit_router
from api.v1.providers import router as providers_router
from api.v1.notifications import router as notifications_router
from api.v1.delivery import router as delivery_router
from api.v1.languages import router as languages_router
from api.v1.media import router as media_router
from api.v1.backups import router as backups_router
from api.v1.crypto import router as crypto_router
from api.v1.reply_buttons import router as reply_buttons_router
from api.v1.resellers import router as resellers_router
from api.v1.reseller_public import router as reseller_public_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(categories_router)
router.include_router(products_router)
router.include_router(stock_router)
router.include_router(orders_router)
router.include_router(payments_router)
router.include_router(users_router)
router.include_router(wallets_router)
router.include_router(commands_router)
router.include_router(messages_router)
router.include_router(buttons_router)
router.include_router(coupons_router)
router.include_router(referrals_router)
router.include_router(support_router)
router.include_router(settings_router)
router.include_router(audit_router)
router.include_router(providers_router)
router.include_router(notifications_router)
router.include_router(delivery_router)
router.include_router(languages_router)
router.include_router(media_router)
router.include_router(backups_router)
router.include_router(crypto_router)
router.include_router(reply_buttons_router)
router.include_router(resellers_router)
router.include_router(reseller_public_router)

