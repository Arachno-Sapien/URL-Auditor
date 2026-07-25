"""
Tests for app.parser — HTML parsing logic.

Tests the pure parsing function directly (no network, no mocking needed).

Covers:
- Happy path: full HTML doc with all fields
- Edge cases: missing title, no meta, empty page, multiple H1s
- Images with and without alt text
- Word count accuracy with scripts/styles stripped
"""

from app.parser import parse_html


class TestParseHtml:
    """Tests for parse_html function."""

    # --- Happy path ---

    def test_full_html_page(self):
        """Complete HTML page should parse all fields correctly."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page Title</title>
            <meta name="description" content="This is a test description">
        </head>
        <body>
            <h1>Main Heading</h1>
            <p>This is some visible text on the page.</p>
            <img src="pic1.jpg" alt="A picture">
            <img src="pic2.jpg" alt="">
            <img src="pic3.jpg">
        </body>
        </html>
        """
        result = parse_html(html)

        assert result["title"] == "Test Page Title"
        assert result["meta_description"] == "This is a test description"
        assert result["h1_count"] == 1
        assert result["total_images"] == 3
        assert result["images_missing_alt"] == 2  # empty alt + missing alt
        assert result["word_count"] > 0

    def test_og_description_fallback(self):
        """Should fall back to og:description if meta description is missing."""
        html = """
        <html>
        <head>
            <title>OG Test</title>
            <meta property="og:description" content="OpenGraph description here">
        </head>
        <body><p>Hello world</p></body>
        </html>
        """
        result = parse_html(html)
        assert result["meta_description"] == "OpenGraph description here"

    # --- Edge cases ---

    def test_missing_title(self):
        """Page with no title tag should return None."""
        html = "<html><head></head><body><p>No title</p></body></html>"
        result = parse_html(html)
        assert result["title"] is None

    def test_no_meta_description(self):
        """Page with no meta description should return None."""
        html = "<html><head><title>Hi</title></head><body><p>No meta</p></body></html>"
        result = parse_html(html)
        assert result["meta_description"] is None

    def test_empty_page(self):
        """Empty HTML should not crash and return zeroed counts."""
        html = "<html><head></head><body></body></html>"
        result = parse_html(html)
        assert result["title"] is None
        assert result["meta_description"] is None
        assert result["h1_count"] == 0
        assert result["total_images"] == 0
        assert result["images_missing_alt"] == 0
        assert result["word_count"] == 0

    def test_multiple_h1_tags(self):
        """Should count all H1 tags on the page."""
        html = """
        <html><body>
            <h1>First</h1>
            <h1>Second</h1>
            <h1>Third</h1>
        </body></html>
        """
        result = parse_html(html)
        assert result["h1_count"] == 3

    def test_no_images(self):
        """Page with no images should report zero."""
        html = "<html><body><p>Just text, no images.</p></body></html>"
        result = parse_html(html)
        assert result["total_images"] == 0
        assert result["images_missing_alt"] == 0

    def test_all_images_have_alt(self):
        """All images with proper alt text should report 0 missing."""
        html = """
        <html><body>
            <img src="a.jpg" alt="Photo A">
            <img src="b.jpg" alt="Photo B">
        </body></html>
        """
        result = parse_html(html)
        assert result["total_images"] == 2
        assert result["images_missing_alt"] == 0

    # --- Word count ---

    def test_word_count_strips_scripts(self):
        """Script content should not be counted in word count."""
        html = """
        <html><body>
            <p>Three visible words</p>
            <script>var x = "these words should not count";</script>
        </body></html>
        """
        result = parse_html(html)
        # "Three visible words" = 3 words
        assert result["word_count"] == 3

    def test_word_count_strips_styles(self):
        """Style content should not be counted in word count."""
        html = """
        <html>
        <head><style>.hidden { display: none; color: red; }</style></head>
        <body>
            <p>Two words</p>
        </body></html>
        """
        result = parse_html(html)
        assert result["word_count"] == 2

    def test_word_count_strips_hidden_elements(self):
        """Elements with hidden attribute should not count."""
        html = """
        <html><body>
            <p>Visible text here</p>
            <div hidden>Hidden text should not count</div>
        </body></html>
        """
        result = parse_html(html)
        assert result["word_count"] == 3

    def test_minimal_html_fragment(self):
        """Should handle HTML fragments gracefully."""
        html = "<p>Just a paragraph with five words here.</p>"
        result = parse_html(html)
        assert result["word_count"] == 7

    # --- Social Previews (Open Graph) ---

    def test_og_image_extracted(self):
        """Should extract og:image if present."""
        html = """
        <html><head>
            <meta property="og:image" content="https://example.com/image.jpg">
        </head><body></body></html>
        """
        result = parse_html(html)
        assert result["og_image"] == "https://example.com/image.jpg"

    def test_twitter_image_fallback(self):
        """Should fall back to twitter:image if og:image is missing."""
        html = """
        <html><head>
            <meta name="twitter:image" content="https://example.com/twit.jpg">
        </head><body></body></html>
        """
        result = parse_html(html)
        assert result["og_image"] == "https://example.com/twit.jpg"
