"""The faux NZB that carries a job spec to the download client.

Newznab's download URL is opaque to Sonarr: the indexer decides what
goes in it, the client decides what to do with it. So it need not be
an NZB at all - but NZB-shaped keeps Sonarr's usenet path happy, and
the spec rides along in a meta tag.
"""

import json
from xml.sax.saxutils import escape

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nzb PUBLIC "-//newzBin//DTD NZB 1.1//EN" \
"http://www.newzbin.com/DTD/nzb/nzb-1.1.dtd">
<nzb xmlns="http://www.newzbin.com/DTD/2003/nzb">
  <head>
    <meta type="name">{name}</meta>
    <meta type="ytdlpspec">{spec}</meta>
  </head>
</nzb>
"""


def job_spec(watch_url, name, defaults):
    """What the client needs in order to fetch. Everything past url
    and name is optional and falls back to the client's own defaults;
    sending them explicitly keeps the indexer in charge of its own
    quality decisions."""
    return {
        "url": watch_url,
        "name": name,
        "format": defaults["format"],
        "subs": defaults["subs"],
        "embed": defaults["embed"],
        "container": defaults["container"],
    }


def render(spec):
    """An NZB-shaped envelope carrying the spec verbatim."""
    return TEMPLATE.format(
        name=escape(spec["name"]),
        spec=escape(json.dumps(spec, ensure_ascii=False)),
    )


def spec_name(series_title, season, episode, episode_title):
    """The file name the client writes, not the release name."""
    return (
        f"{series_title} - S{season:02d}E{episode:02d} - {episode_title}"
    )
