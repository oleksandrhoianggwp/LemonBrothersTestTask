import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True, slots=True)
class ScrapedProduct:
    title: str
    category: str
    price: Decimal | None
    rating: float | None
    reviews_count: int
    product_url: str
    image_url: str
    asin: str | None


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def parse_price(value: str | None) -> Decimal | None:
    if not value:
        return None
    compact = value.replace("\u00a0", "").replace(" ", "")
    match = re.search(r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?", compact)
    if not match:
        return None
    numeric = match.group(0)
    if "," in numeric and "." in numeric:
        numeric = numeric.replace(",", "") if numeric.rfind(".") > numeric.rfind(",") else numeric.replace(".", "").replace(",", ".")
    elif numeric.count(",") == 1 and len(numeric.rsplit(",", 1)[1]) <= 2:
        numeric = numeric.replace(",", ".")
    else:
        numeric = numeric.replace(",", "")
    try:
        return Decimal(numeric)
    except InvalidOperation:
        return None


def parse_rating(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-5](?:[.,]\d+)?)", value)
    if not match:
        return None
    return min(5.0, max(0.0, float(match.group(1).replace(",", "."))))


def parse_review_count(value: str | None) -> int:
    if not value:
        return 0
    lowered = value.lower().replace("\u00a0", " ")
    multiplier = 1_000 if re.search(r"\d\s*k\b", lowered) else 1
    match = re.search(r"([\d.,\s]+)", lowered)
    if not match:
        return 0
    numeric = match.group(1).strip()
    if multiplier > 1:
        try:
            return int(float(numeric.replace(",", ".").replace(" ", "")) * multiplier)
        except ValueError:
            return 0
    digits = re.sub(r"\D", "", numeric)
    return int(digits) if digits else 0


def _text(card: Tag, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        element = card.select_one(selector)
        if element:
            value = element.get("aria-label") or element.get_text(" ", strip=True)
            if value:
                return normalize_whitespace(str(value))
    return None


def _canonical_product_url(url: str, base_url: str) -> tuple[str, str | None]:
    absolute = urljoin(base_url, url)
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", absolute, re.I)
    if match:
        asin = match.group(1).upper()
        origin = f"{urlsplit(absolute).scheme}://{urlsplit(absolute).netloc}"
        return f"{origin}/dp/{asin}", asin
    split = urlsplit(absolute)
    return f"{split.scheme}://{split.netloc}{split.path}", None


def parse_amazon_html(html: str, base_url: str) -> list[ScrapedProduct]:
    soup = BeautifulSoup(html, "html.parser")
    category = _text(
        soup,
        ("#zg_banner_text", "h1", "._cDEzb_card-title_2sYgw", "[data-testid='category-title']"),
    ) or "Amazon Best Sellers"
    cards = soup.select(
        "[data-asin]:has(a[href*='/dp/']), .zg-grid-general-faceout, "
        ".p13n-sc-uncoverable-faceout"
    )
    products: list[ScrapedProduct] = []
    seen: set[str] = set()
    for card in cards:
        try:
            link = card.select_one("a[href*='/dp/'], a[href*='/gp/product/']")
            image = card.select_one("img")
            if link is None or image is None or not link.get("href"):
                continue
            title = _text(
                card,
                (
                    "._cDEzb_p13n-sc-css-line-clamp-3_g3dy1",
                    ".p13n-sc-truncate-desktop-type2",
                    ".a-size-base-plus",
                    ".a-size-medium",
                ),
            ) or normalize_whitespace(str(image.get("alt") or ""))
            image_url = str(image.get("src") or image.get("data-src") or "").strip()
            if not title or not image_url:
                continue
            product_url, url_asin = _canonical_product_url(str(link["href"]), base_url)
            asin = str(card.get("data-asin") or "").strip().upper() or url_asin
            unique_key = asin or product_url
            if unique_key in seen:
                continue
            seen.add(unique_key)
            price_text = _text(card, (".p13n-sc-price", ".a-price .a-offscreen", ".a-price"))
            rating_text = _text(card, (".a-icon-alt", "[aria-label*='out of 5']"))
            reviews_text = _text(
                card,
                (
                    "a[href*='customerReviews'] .a-size-small",
                    "a[href*='#customerReviews'] span",
                    ".a-size-small",
                ),
            )
            products.append(
                ScrapedProduct(
                    title=title,
                    category=category,
                    price=parse_price(price_text),
                    rating=parse_rating(rating_text),
                    reviews_count=parse_review_count(reviews_text),
                    product_url=product_url,
                    image_url=urljoin(base_url, image_url),
                    asin=asin or None,
                )
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    return products
