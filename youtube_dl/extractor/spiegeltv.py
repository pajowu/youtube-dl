# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (compat_urllib_parse_urlparse, compat_urllib_parse_urlencode)
from ..utils import (
    determine_ext,
    float_or_none,
)
import hashlib
import re

class SpiegeltvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?spiegel\.tv/(?:#/)?videos/(?P<id>[0-9]+)([\-a-z0-9]+)'
    _TESTS = [{
        'url': 'http://www.spiegel.tv/videos/199901-wenn-teenager-muetter-werden',
        'info_dict': {
            'title': 'Wenn Teenager Mütter werden',
            'subtitle': 'Kindeskinder',
            'description': 'Im Haus Regenbogen leben in der Nähe von Flensburg 13 junge Mütter. Die Teenager kommen fast alle aus zerrütteten Verhältnissen. Für viele ist die frühe Mutterschaft eine Art Flucht aus ihrem vorherigen Leben. Sie träumen von einer eigenen heilen Familie, wollen ihren Kindern die Geborgenheit geben, die sie nie hatten. Doch in den wenigsten Fällen erfüllt sich der Wunsch. Eine SPIEGEL-TV-Reportage von Sanja Hardinghaus.',
            'duration': 2689,
            'id': '199901',
            'ext': 'mp4'
        }
    }]

    def _real_extract(self, url):
        if '/#/' in url:
            url = url.replace('/#/', '/')
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        domain_id = self._html_search_regex(r'http://require.nexx.cloud/([0-9]+)/one', webpage, 'domain_id')
        domain_secret = self._html_search_regex(r'"hash":"([A-Z0-9]+)"', webpage, 'domain_secret')
        device_id = self._html_search_regex(r'"nxp_devh":"([^"]+)"', webpage, 'device_id')

        client_data_json_url = "https://api.nexx.cloud/v3/{did}/session/init".format(did=domain_id)
        data = compat_urllib_parse_urlencode({"nxp_devh":device_id}).encode()

        client_data = self._download_json(
            client_data_json_url, video_id,
            note='Downloading client information',
            data=data)

        client_id = client_data["result"]["general"]["cid"]

        request_token = hashlib.md5("byid".encode()+domain_id.encode()+domain_secret.encode()).hexdigest()
        request_headers = {"X-Request-CID":client_id,"X-Request-Token":request_token}

        meta_json_url = "https://api.nexx.cloud/v3/{did}/videos/byid/{vid}".format(did=domain_id,vid=video_id)
        request_data = {"additionalfields":"subtitle,description","addStreamDetails":"1"}
        metadata = self._download_json(
            meta_json_url, video_id,
            note='Downloading metadata json', headers=request_headers,data=compat_urllib_parse_urlencode(request_data).encode())
        duration_split = metadata["result"]["general"]["runtime"].split(":")
        duration = int(duration_split[0])*60*60 + int(duration_split[1])*60 + int(duration_split[2])

        streamdata = metadata["result"]["streamdata"]
        doc = "http://{cdn_host}/{cdn_vid}/{vid}_src.ism/Manifest(format=mpd-time-csf)".format(
            cdn_host=streamdata["cdnShieldHTTP"], cdn_vid=streamdata["azureLocator"], vid=video_id)
        formats = self._extract_mpd_formats(doc, video_id)
        self._sort_formats(formats)
        return {
            "id":video_id,
            "title":metadata["result"]["general"]["title"],
            "subtitle":metadata["result"]["general"]["subtitle"],
            "description":metadata["result"]["general"]["description"],
            "duration":duration,
            "formats":formats,
            "thumbnails":[{"url":metadata["result"]["imagedata"]["thumb"]}]
        }
