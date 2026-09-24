import unittest

from nrkarr import hls

MASTER = """#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud1",LANGUAGE="und",NAME="Undetermined",CHANNELS="2",AUTOSELECT=YES,DEFAULT=YES,URI="sc/A0_index.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="sub1",LANGUAGE="no",NAME="Norsk",AUTOSELECT=YES,DEFAULT=YES,CHARACTERISTICS="public.accessibility.transcribes-spoken-dialog",URI="sc/s0_index.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="sub1",LANGUAGE="no",NAME="Norsk – kun ved annet språk",URI="sc/s1_index.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="sub1",LANGUAGE="no",NAME="Norsk – med lydbeskrivelser",AUTOSELECT=YES,CHARACTERISTICS="public.accessibility.describes-music-and-sound",URI="sc/s2_index.m3u8"
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud2",LANGUAGE="und",NAME="Undetermined",CHANNELS="2",URI="sc/A1_index.m3u8"
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud3",LANGUAGE="und",NAME="Undetermined",CHANNELS="6",URI="sc/A2_index.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=1300000,CODECS="avc1",RESOLUTION=640x360,AUDIO="aud1",SUBTITLES="sub1"
sc/V1_index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=9500000,CODECS="avc1",RESOLUTION=1920x1080,AUDIO="aud2",SUBTITLES="sub1"
sc/V5_index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=9600000,CODECS="hvc1",RESOLUTION=1920x1080,AUDIO="aud3",SUBTITLES="sub1"
sc/V6_index.m3u8
"""
URL = "https://cdn.example/open/ps/x/y.smil/cmaf.m3u8"


class MasterTest(unittest.TestCase):
    def test_master_sits_beside_the_muxed_asset(self):
        self.assertEqual(
            hls.master_url("https://cdn.example/open/ps/x/y.smil/muxed.m3u8?adap=small&s=0&aco=aac"),
            URL,
        )

    def test_subtitle_renditions_with_absolute_urls(self):
        renditions = hls.subtitle_renditions(MASTER, URL)

        self.assertEqual([r["name"] for r in renditions],
                         ["Norsk", "Norsk – kun ved annet språk", "Norsk – med lydbeskrivelser"])
        self.assertEqual(renditions[0]["url"], "https://cdn.example/open/ps/x/y.smil/sc/s0_index.m3u8")
        self.assertTrue(renditions[0]["default"])
        self.assertIn("describes-music-and-sound", renditions[2]["characteristics"])

    def test_entries_carry_the_flags_players_act_on(self):
        entries = hls.subtitle_entries(hls.subtitle_renditions(MASTER, URL), "kun ved annet språk")

        self.assertEqual([e["flags"] for e in entries], [["default"], ["forced"], ["hearing_impaired"]])
        self.assertEqual({e["language"] for e in entries}, {"nob"})
        self.assertEqual(entries[2]["title"], "Norsk – med lydbeskrivelser")

    def test_quoted_attributes_with_commas_survive(self):
        found = hls.attributes('#EXT-X-MEDIA:TYPE=SUBTITLES,NAME="A, B",URI="u"')

        self.assertEqual(found["NAME"], "A, B")

    def test_language_tags(self):
        self.assertEqual(hls.language_tag("nb"), "nob")
        self.assertEqual(hls.language_tag("sme"), "sme")
        self.assertEqual(hls.language_tag(""), "und")


class AudioGroupTest(unittest.TestCase):
    def test_groups_carry_channels_and_the_bandwidth_that_uses_them(self):
        groups = {g["group"]: g for g in hls.audio_groups(MASTER)}

        self.assertEqual(groups["aud3"]["channels"], 6)
        self.assertEqual(groups["aud1"]["bandwidth"], 1300000)
        self.assertEqual(groups["aud2"]["bandwidth"], 9500000)

    def test_selector_picks_the_high_bitrate_stereo_group(self):
        groups = hls.audio_groups(MASTER)

        self.assertEqual(hls.audio_selector(groups, 2), "bestaudio[format_id^=aud2]")
        self.assertEqual(hls.audio_selector(groups, 6), "bestaudio[format_id^=aud3]")
        self.assertIsNone(hls.audio_selector(groups, 8))
