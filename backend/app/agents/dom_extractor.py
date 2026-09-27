from typing import Any
import re
from pydantic import BaseModel

class ExtractedElement(BaseModel):
    index: int
    tag: str
    element_type: str | None = None
    id: str | None = None
    name: str | None = None
    placeholder: str | None = None
    role: str | None = None
    aria_label: str | None = None
    text: str = ""
    value: str | None = None
    selector: str
    is_visible: bool = True
    is_disabled: bool = False

class DOMObservation(BaseModel):
    url: str
    title: str
    elements: list[ExtractedElement] = []
    text_summary: str = ""
    alerts: list[str] = []

    def get_element_by_index(self, index: int) -> ExtractedElement | None:
        for el in self.elements:
            if el.index == index:
                return el
        return None

    def get_selector(self, target: int | str) -> str:
        """Resolve either an integer element index or a direct CSS/XPath selector."""
        if isinstance(target, int):
            el = self.get_element_by_index(target)
            if el:
                return el.selector
            raise ValueError(f"Element index [{target}] not found in current DOM observation.")
        # If it's a string that is an integer representation (e.g. "1")
        if isinstance(target, str) and target.strip().isdigit():
            idx = int(target.strip())
            el = self.get_element_by_index(idx)
            if el:
                return el.selector
        return str(target)


EXTRACT_JS = """
(() => {
    const isVisible = (elem) => {
        if (!elem) return false;
        const style = window.getComputedStyle(elem);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        const rect = elem.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    };

    const getOptimalSelector = (el) => {
        if (el.id) return `#${CSS.escape(el.id)}`;
        if (el.getAttribute('data-testid')) return `[data-testid="${CSS.escape(el.getAttribute('data-testid'))}"]`;
        if (el.getAttribute('name')) return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.getAttribute('name'))}"]`;
        if (el.getAttribute('aria-label')) return `[aria-label="${CSS.escape(el.getAttribute('aria-label'))}"]`;
        if (el.getAttribute('placeholder')) return `[placeholder="${CSS.escape(el.getAttribute('placeholder'))}"]`;
        
        // Path selector
        let path = [];
        let curr = el;
        while (curr && curr.nodeType === Node.ELEMENT_NODE && curr.tagName.toLowerCase() !== 'body') {
            let selector = curr.tagName.toLowerCase();
            if (curr.id) {
                selector += `#${CSS.escape(curr.id)}`;
                path.unshift(selector);
                break;
            } else {
                let sib = curr, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.tagName.toLowerCase() === selector) nth++;
                }
                if (nth > 1) selector += `:nth-of-type(${nth})`;
            }
            path.unshift(selector);
            curr = curr.parentElement;
        }
        return path.join(' > ');
    };

    const candidateSelector = 'button, a, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [role="alert"], h1, h2, h3, [tabindex="0"]';
    const rawElements = Array.from(document.querySelectorAll(candidateSelector));
    
    let index = 1;
    const extracted = [];
    const alerts = [];

    for (const el of rawElements) {
        if (!isVisible(el)) continue;
        
        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role') || '';
        const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 100);
        const value = el.value !== undefined && el.value !== null ? String(el.value).slice(0, 100) : null;
        
        if (role === 'alert' || el.classList.contains('error') || el.classList.contains('alert')) {
            alerts.push(text);
        }

        extracted.push({
            index: index++,
            tag: tag,
            element_type: el.getAttribute('type') || null,
            id: el.id || null,
            name: el.getAttribute('name') || null,
            placeholder: el.getAttribute('placeholder') || null,
            role: role || null,
            aria_label: el.getAttribute('aria-label') || null,
            text: text,
            value: value,
            selector: getOptimalSelector(el),
            is_visible: true,
            is_disabled: el.disabled || el.getAttribute('aria-disabled') === 'true'
        });
    }

    return {
        url: window.location.href,
        title: document.title,
        elements: extracted,
        alerts: alerts
    };
})()
"""

class DOMExtractor:
    """Extracts compact, LLM-optimized representations of interactive DOM elements."""

    @classmethod
    async def extract_from_page(cls, page: Any) -> DOMObservation:
        """Runs evaluation in Playwright page to extract interactive DOM snapshot."""
        try:
            data = await page.evaluate(EXTRACT_JS)
            elements = [ExtractedElement(**item) for item in data.get("elements", [])]
            alerts = data.get("alerts", [])
            
            # Format text summary
            lines = [
                f"Page URL: {data.get('url', '')}",
                f"Page Title: {data.get('title', '')}",
            ]
            if alerts:
                lines.append("Alerts/Errors on Page:")
                for alert in alerts:
                    lines.append(f"  ⚠️  {alert}")
            
            lines.append("Interactive Elements:")
            if not elements:
                lines.append("  (No interactive elements detected)")
            else:
                for el in elements:
                    attrs = []
                    if el.element_type:
                        attrs.append(f'type="{el.element_type}"')
                    if el.id:
                        attrs.append(f'id="{el.id}"')
                    if el.name:
                        attrs.append(f'name="{el.name}"')
                    if el.placeholder:
                        attrs.append(f'placeholder="{el.placeholder}"')
                    if el.role and el.role not in ('button', 'link'):
                        attrs.append(f'role="{el.role}"')
                    if el.aria_label:
                        attrs.append(f'aria-label="{el.aria_label}"')
                    if el.value:
                        attrs.append(f'value="{el.value}"')
                    if el.is_disabled:
                        attrs.append('DISABLED')
                    
                    attr_str = (" " + " ".join(attrs)) if attrs else ""
                    text_str = f' "{el.text}"' if el.text else ""
                    lines.append(f"  [{el.index}] <{el.tag}{attr_str}>{text_str}</{el.tag}>")
            
            text_summary = "\n".join(lines)
            return DOMObservation(
                url=data.get("url", ""),
                title=data.get("title", ""),
                elements=elements,
                text_summary=text_summary,
                alerts=alerts
            )
        except Exception as e:
            # Fallback for empty or detached page
            return DOMObservation(
                url=getattr(page, "url", "about:blank"),
                title="",
                elements=[],
                text_summary=f"Page URL: {getattr(page, 'url', 'about:blank')}\nError inspecting DOM: {str(e)}",
                alerts=[f"DOM Inspection error: {str(e)}"]
            )
