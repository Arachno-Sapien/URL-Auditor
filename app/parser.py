"""
HTML parser — extracts audit metrics from raw HTML using BeautifulSoup.

Pure function: takes HTML string in, returns data dict out. No side effects.
This makes it trivially testable without mocking anything.
"""

from bs4 import BeautifulSoup


def parse_html(html):
    """
    Parse an HTML string and extract audit metrics.

    Args:
        html (str): Raw HTML content.

    Returns:
        dict: Parsed audit data with keys:
            - title (str|None)
            - meta_description (str|None)
            - h1_count (int)
            - total_images (int)
            - images_missing_alt (int)
            - word_count (int)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Page title - check og:title first, then fallback to <title>
    title = None
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    else:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

    # Meta description — check both name and property (og:description)
    meta_desc = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()
    else:
        og_tag = soup.find("meta", attrs={"property": "og:description"})
        if og_tag and og_tag.get("content"):
            meta_desc = og_tag["content"].strip()
            
    # Open Graph Image
    og_image = None
    og_img_tag = soup.find("meta", attrs={"property": "og:image"})
    if og_img_tag and og_img_tag.get("content"):
        og_image = og_img_tag["content"].strip()
    else:
        twitter_img_tag = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_img_tag and twitter_img_tag.get("content"):
            og_image = twitter_img_tag["content"].strip()

    # H1 count
    h1_count = len(soup.find_all("h1"))

    # Images missing alt text
    images = soup.find_all("img")
    total_images = len(images)
    images_missing_alt = sum(
        1 for img in images if not img.get("alt", "").strip()
    )

    # Approximate word count from visible text
    # Remove non-visible elements before counting
    word_count = _count_visible_words(html)

    return {
        "title": title,
        "meta_description": meta_desc,
        "h1_count": h1_count,
        "total_images": total_images,
        "images_missing_alt": images_missing_alt,
        "word_count": word_count,
        "og_image": og_image,
    }


def _count_visible_words(html):
    """
    Count approximate words in visible page text.

    Strips script, style, noscript, and SVG elements before counting.
    Collapses whitespace and splits on word boundaries.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove elements that don't contribute visible text
    for tag in soup.find_all(["script", "style", "noscript", "svg", "head"]):
        tag.decompose()

    # Also remove hidden elements
    for tag in soup.find_all(attrs={"hidden": True}):
        tag.decompose()
    for tag in soup.find_all(attrs={"aria-hidden": "true"}):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)

    if not text:
        return 0

    # Split on whitespace and count
    words = text.split()
    return len(words)
