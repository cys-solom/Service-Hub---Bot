"""Backend CMS template renderer — renders notification templates from DB."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.cms import MessageTemplate

logger = logging.getLogger(__name__)


async def render(db: AsyncSession, key: str, lang: str = "en", **kwargs) -> str:
    """Render a CMS template with placeholder substitution."""
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.key == key,
            MessageTemplate.is_active == True,
            MessageTemplate.is_deleted == False,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        logger.warning(f"[CMS] Template '{key}' not found")
        return ""

    content = template.content
    if lang != "en" and template.content_i18n:
        if isinstance(template.content_i18n, dict) and lang in template.content_i18n:
            content = template.content_i18n[lang]

    for k, v in kwargs.items():
        placeholder = "{" + k + "}"
        if placeholder in content:
            content = content.replace(placeholder, str(v))

    return content
