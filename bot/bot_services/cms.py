"""CMS Message Template loader — supports Premium Emoji (<tg-emoji>)"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.cms import MessageTemplate

logger = logging.getLogger(__name__)


async def get_template(session: AsyncSession, key: str) -> MessageTemplate | None:
    """Get a message template by key from DB"""
    result = await session.execute(
        select(MessageTemplate).where(
            MessageTemplate.key == key,
            MessageTemplate.is_active == True,
            MessageTemplate.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def render(session: AsyncSession, key: str, lang: str = "en", **kwargs) -> str:
    """Render a message template with placeholders.
    
    Supports:
    - HTML tags: <b>, <i>, <code>, <pre>, <a>, etc.
    - Telegram Premium Emoji: <tg-emoji emoji-id="ID">emoji</tg-emoji>
    - Placeholders: {store_name}, {product_name}, etc.
    """
    template = await get_template(session, key)
    if not template:
        # Fallback to hardcoded if template not in DB yet
        logger.warning(f"[CMS] Template '{key}' not found, using fallback")
        return f"[{key}]"

    # Get content for language
    content = template.content
    if lang != "en" and template.content_i18n:
        if isinstance(template.content_i18n, dict) and lang in template.content_i18n:
            content = template.content_i18n[lang]

    # Replace placeholders — use safe replacement that doesn't break HTML/tg-emoji
    for k, v in kwargs.items():
        placeholder = "{" + k + "}"
        if placeholder in content:
            content = content.replace(placeholder, str(v))

    # Safety: fix unclosed <tg-emoji> tags (Telegram will reject malformed HTML)
    open_count = content.count("<tg-emoji")
    close_count = content.count("</tg-emoji>")
    if open_count > close_count:
        import re
        # Find unclosed tg-emoji and add closing tags
        for _ in range(open_count - close_count):
            content += "</tg-emoji>"
        logger.warning(f"[CMS] Fixed {open_count - close_count} unclosed <tg-emoji> in '{key}'")

    # Safety: Telegram max message length is 4096 chars
    if len(content) > 4000:
        logger.warning(f"[CMS] Template '{key}' is suspiciously long ({len(content)} chars), truncating")
        content = content[:4000]

    return content


async def update_template(session: AsyncSession, key: str, content: str,
                          content_ar: str = None) -> bool:
    """Update a message template"""
    from sqlalchemy.orm.attributes import flag_modified
    
    template = await get_template(session, key)
    if not template:
        return False

    template.content = content
    flag_modified(template, "content")
    
    if content_ar:
        current = {}
        if template.content_i18n and isinstance(template.content_i18n, dict):
            current = dict(template.content_i18n)
        current["ar"] = content_ar
        template.content_i18n = current
        flag_modified(template, "content_i18n")
    
    await session.flush()
    await session.commit()
    return True


async def list_templates(session: AsyncSession, group: str = None) -> list[dict]:
    """List all message templates"""
    query = select(MessageTemplate).where(
        MessageTemplate.is_active == True,
        MessageTemplate.is_deleted == False,
    )
    if group:
        query = query.where(MessageTemplate.group == group)
    
    result = await session.execute(query.order_by(MessageTemplate.key))
    templates = result.scalars().all()

    return [{
        "id": str(t.id),
        "key": t.key,
        "content": t.content,
        "content_i18n": t.content_i18n if isinstance(t.content_i18n, dict) else {},
        "group": t.group,
        "type": t.type,
    } for t in templates]
