"""Newznab XML: the capabilities document and the search results."""

from email.utils import format_datetime
from xml.sax.saxutils import escape, quoteattr

CATEGORY_TV = "5000"

CAPS = """<?xml version="1.0" encoding="UTF-8"?>
<caps>
  <server title="nrkarr" />
  <limits max="100" default="100" />
  <searching>
    <search available="yes" supportedParams="q" />
    <tv-search available="yes" supportedParams="q,tvdbid,season,ep" />
    <movie-search available="no" supportedParams="q" />
    <audio-search available="no" supportedParams="q" />
    <book-search available="no" supportedParams="q" />
  </searching>
  <categories>
    <category id="5000" name="TV">
      <subcat id="5040" name="TV/HD" />
    </category>
  </categories>
</caps>
"""


def attribute(name, value):
    return f'      <newznab:attr name="{name}" value={quoteattr(str(value))} />'


def item(release):
    """One release. Sonarr reads title, size and the enclosure URL;
    the attrs let it match without reparsing the name."""
    attributes = [
        attribute("category", CATEGORY_TV),
        attribute("size", release["size"]),
        attribute("tvdbid", release["tvdb_id"]),
        attribute("season", release["season"]),
        attribute("episode", release["episode"]),
    ]

    return "\n".join([
        "    <item>",
        f"      <title>{escape(release['title'])}</title>",
        f"      <guid isPermaLink=\"false\">{escape(release['guid'])}</guid>",
        f"      <link>{escape(release['link'])}</link>",
        f"      <pubDate>{release['published']}</pubDate>",
        (
            f"      <enclosure url={quoteattr(release['link'])} "
            f"length=\"{release['size']}\" "
            'type="application/x-nzb" />'
        ),
        *attributes,
        "    </item>",
    ])


def feed(releases):
    items = "\n".join(item(release) for release in releases)

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" '
        'xmlns:newznab="http://www.newznab.com/DTD/2010/feeds/attributes/">',
        "  <channel>",
        "    <title>nrkarr</title>",
        "    <description>NRK TV as a Newznab indexer</description>",
        items,
        "  </channel>",
        "</rss>",
        "",
    ])


def published(release_date):
    """psapi gives an ISO timestamp; RSS wants RFC 822."""
    from datetime import datetime

    if not release_date:
        return ""

    return format_datetime(datetime.fromisoformat(release_date))
