# -*- coding: utf-8 -*-
"""
Arabic Shows Kodi Addon - v1.0.6
Live Arabic TV channels + YouTube drama content
Syrian, Lebanese, Egyptian, Iraqi, Jordanian, Arabic Drama, Music
Made with love for Walaa <3
"""

import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

addon_handle = int(sys.argv[1])

# ==============================================================================
# LIVE TV CHANNELS (from iptv-org — verified July 2026)
# Arabic name is in 'ar' field for metadata only — display uses English
# to avoid missing-glyph squares (Kodi default font has no Arabic).
# ==============================================================================

LIVE_CHANNELS = [
    # --- Syrian Channels ---
    {
        'name': 'Al-Souriya TV',
        'ar': 'السورية',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-al-souriya-tv/e3150760fa5fd62776225433b8c3d406/index.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Syria TV',
        'ar': 'سوريا تي في',
        'url': 'https://live.kwikmotion.com/syriatvlive/syriatv.smil/playlist_dvr.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Halab Today TV',
        'ar': 'حلب اليوم',
        'url': 'https://halabtoday-live.lg.mncdn.com/halabtoday/livestream/playlist.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Al Mayadeen',
        'ar': 'الميادين',
        'url': 'https://mdnlv.cdn.octivid.com/almdn/smil:mpegts.stream.smil/playlist.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Al Araby TV',
        'ar': 'العربي',
        'url': 'https://live.kwikmotion.com/alaraby1live/alaraby_abr/playlist.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Al Araby TV 2',
        'ar': 'العربي 2',
        'url': 'https://live.kwikmotion.com/alaraby2live/alaraby2.smil/playlist.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Bab Al Hara',
        'ar': 'باب الحارة',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx010/playlist.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Althania (Syria 2)',
        'ar': 'الثانية',
        'url': 'https://live.kwikmotion.com/syriatv02live/syriatv02.smil/playlist.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Alikhbaria Syria',
        'ar': 'الإخبارية سوريا',
        'url': 'http://185.9.2.18/chid_423/index.m3u8',
        'group': 'Syrian',
    },
    {
        'name': 'Damascus Radio',
        'ar': 'إذاعة دمشق',
        'url': 'https://radiodamascus.ortas.live/RDimshq/RDimshqLive/playlist.m3u8',
        'group': 'Syrian',
    },
    # --- Lebanese Channels ---
    {
        'name': 'MTV Lebanon',
        'ar': 'إم تي في',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mtv-lebanon/b8ebb2a5affb812f1541712adde10e26/index.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'LBC International',
        'ar': 'إل بي سي',
        'url': 'http://185.9.2.18/chid_327/index.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'LBC International HD',
        'ar': 'إل بي سي HD',
        'url': 'http://185.9.2.18/chid_521/index.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'Al Jadeed',
        'ar': 'الجديد',
        'url': 'http://185.9.2.18/chid_391/mono.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'OTV Lebanon',
        'ar': 'أو تي في',
        'url': 'https://otv.hibridcdn.net/otv/tv_abr/playlist.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'Future TV',
        'ar': 'تلفزيون المستقبل',
        'url': 'https://live.kwikmotion.com/futurelive/ftv.smil/playlist.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'Voice of Lebanon',
        'ar': 'صوت لبنان',
        'url': 'https://svs.itworkscdn.net/vdltvlive/vdltv.smil/playlist.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'Red TV Lebanon',
        'ar': 'ريد تي في',
        'url': 'https://live.kwikmotion.com/redtvlive/redtv.smil/playlist.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'Maraya',
        'ar': 'مرايا',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx008/playlist.m3u8',
        'group': 'Lebanese',
    },
    {
        'name': 'Al Manar',
        'ar': 'المنار',
        'url': 'https://edge.fastpublish.me/live/index.m3u8',
        'group': 'Lebanese',
    },
    # --- Egyptian Channels ---
    {
        'name': 'MBC 1 Egypt',
        'ar': 'إم بي سي 1 مصر',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-1-na/eec141533c90dd34722c503a296dd0d8/index.m3u8',
        'group': 'Egyptian',
    },
    {
        'name': 'MBC Masr',
        'ar': 'إم بي سي مسر',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr/956eac069c78a35d47245db6cdbb1575/index.m3u8',
        'group': 'Egyptian',
    },
    {
        'name': 'MBC Masr 2',
        'ar': 'إم بي سي مسر 2',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr-2/754931856515075b0aabf0e583495c68/index.m3u8',
        'group': 'Egyptian',
    },
    {
        'name': 'MBC Masr USA',
        'ar': 'إم بي سي مسر أمريكا',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr-usa/cd8d40acdab28aac0582faa3bd3983f1/index.m3u8',
        'group': 'Egyptian',
    },
    {
        'name': 'Al Masriyah',
        'ar': 'المصرية',
        'url': 'http://185.9.2.18/chid_247/index.m3u8',
        'group': 'Egyptian',
    },
    {
        'name': 'CBC Sofra',
        'ar': 'سي بي سي سفره',
        'url': 'https://flu.systemnet.tv/CBCSofra/index.m3u8',
        'group': 'Egyptian',
    },
    {
        'name': 'Mekameleen TV',
        'ar': 'مكمملين',
        'url': 'https://mn-nl.mncdn.com/mekameleen/smil:mekameleentv.smil/playlist.m3u8',
        'group': 'Egyptian',
    },
    # --- Arabic Drama Channels ---
    {
        'name': 'MBC 1',
        'ar': 'إم بي سي 1',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-1/15cf99af5de54063fdabfefe66adc075/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC 4',
        'ar': 'إم بي سي 4',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-4/24f134f1cd63db9346439e96b86ca6ed/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC 5',
        'ar': 'إم بي سي 5',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-5/ee6b000cee0629411b666ab26cb13e9b/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC Drama',
        'ar': 'إم بي سي دراما',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-drama/2c28a458e2f3253e678b07ac7d13fe71/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC+ Drama',
        'ar': 'إم بي سي بلس دراما',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-plus-drama/e37251ec2aac8f6c98f75cd0fa37cd28/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC Masr Drama',
        'ar': 'إم بي سي مسر دراما',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr-drama/567b703c19ede6598222de81b0e4508b/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC Drama USA',
        'ar': 'إم بي سي دراما أمريكا',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-drama-usa/ea2f5db904aff224b7066e59c7f585a2/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC Iraq',
        'ar': 'إم بي سي العراق',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-iraq/e38c44b1b43474e1c39cb5b90203691e/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'MBC Mood',
        'ar': 'إم بي سي مود',
        'url': 'https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-mood/78367bf48ccdba501d0d014a10c21031/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'CBC Drama',
        'ar': 'سي بي سي دراما',
        'url': 'https://flu.systemnet.tv/CBCDrama/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'CBC',
        'ar': 'سي بي سي',
        'url': 'https://flu.systemnet.tv/CBC/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Roya Drama',
        'ar': 'رويا دراما',
        'url': 'https://playlist.fasttvcdn.com/pl/a2le4pbpa6rpzv147haf4w/drama/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Jordan Drama',
        'ar': 'الأردن دراما',
        'url': 'https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Drama/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Roya Comedy',
        'ar': 'رويا كوميدي',
        'url': 'https://playlist.fasttvcdn.com/pl/toa2uuhhygheuly7xtuqrg/roya-comedy/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Jordan Comedy',
        'ar': 'كوميديا الأردن',
        'url': 'https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Comedy/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Aflam (Movies)',
        'ar': 'أفلام',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx001/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Movies Action',
        'ar': 'أفلام أكشن',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx011/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Movies Thriller',
        'ar': 'أفلام إثارة',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx012/playlist.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Fillka TV',
        'ar': 'فيلكا',
        'url': 'https://amixtv.com/fillkatvhd/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Mix Hollywood',
        'ar': 'مكس هوليوود',
        'url': 'https://ml-pull-hwc.myco.io/MixTV/hls/index.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Spacetoon',
        'ar': 'سبيستون',
        'url': 'https://live-uae-next.spacetoongo.com/ST_MENA_NEXT/hls/r9p2hjipmw2kl.m3u8',
        'group': 'Arabic Drama',
    },
    {
        'name': 'Ajyal TV',
        'ar': 'أجيال',
        'url': 'http://htvajyal.mada.ps:8888/ajyal/index.m3u8',
        'group': 'Arabic Drama',
    },
    # --- Iraqi Channels ---
    {
        'name': 'Al Iraqia',
        'ar': 'العراقية',
        'url': 'https://imn-live.esite-lab.com/hls/iraqia-general.m3u8',
        'group': 'Iraq',
    },
    {
        'name': 'Al Iraqia News',
        'ar': 'العراقية الأخبارية',
        'url': 'https://imn-live.esite-lab.com/hls/iraqia-news.m3u8',
        'group': 'Iraq',
    },
    {
        'name': 'Al Iraqia Sport',
        'ar': 'العراقية الرياضية',
        'url': 'https://imn-live.esite-lab.com/hls/iraqia-sports-1.m3u8',
        'group': 'Iraq',
    },
    {
        'name': 'Alhurra Iraq',
        'ar': 'الحرة العراق',
        'url': 'https://mbn-ingest-worldsafe.akamaized.net/hls/live/2038899/MBN_Iraq_Worldsafe_HLS/master.m3u8',
        'group': 'Iraq',
    },
    {
        'name': 'Iraq Future',
        'ar': 'عراق المستقبل',
        'url': 'https://viewmedia7219.bozztv.com/wmedia/viewmedia100/web_040/Stream/playlist.m3u8',
        'group': 'Iraq',
    },
    # --- Jordan Channels ---
    {
        'name': 'Jordan Satellite Channel',
        'ar': 'قناة الأردن',
        'url': 'https://jrtv-live.ercdn.net/jordanhd/jordanhd.m3u8',
        'group': 'Jordan',
    },
    {
        'name': 'Jordan Archive',
        'ar': 'أرشيف الأردن',
        'url': 'https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Archive/playlist.m3u8',
        'group': 'Jordan',
    },
    {
        'name': 'Jordan Kitchen',
        'ar': 'مطبخ الأردن',
        'url': 'https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/cooking/playlist.m3u8',
        'group': 'Jordan',
    },
    {
        'name': 'Jordan Tourism',
        'ar': 'سياحة الأردن',
        'url': 'https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Tourism/playlist.m3u8',
        'group': 'Jordan',
    },
    {
        'name': 'Roya Kids',
        'ar': 'رويا كيدز',
        'url': 'https://playlist.fasttvcdn.com/pl/ptllxjd03j6g9oxxjdfapg/roya-kids/playlist.m3u8',
        'group': 'Jordan',
    },
    {
        'name': 'Roya Kids Originals',
        'ar': 'رويا كيدز الأصلية',
        'url': 'https://playlist.fasttvcdn.com/pl/ptllxjd03j6g9oxxjdfapg/roya-kids-originals/playlist.m3u8',
        'group': 'Jordan',
    },
    {
        'name': 'Roya Kitchen',
        'ar': 'مطبخ رويا',
        'url': 'https://playlist.fasttvcdn.com/pl/toa2uuhhygheuly7xtuqrg/roya-kitchen/playlist.m3u8',
        'group': 'Jordan',
    },
    # --- Arabic Music Video Channels ---
    {
        'name': 'Aghani Aghani TV',
        'ar': 'أغاني أغاني',
        'url': 'https://cdn.streamlane.tv/hls/aghanitv/index.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Arabica TV',
        'ar': 'عربيكا',
        'url': 'http://istream.binarywaves.com:8081/hls/arabica/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'El Radio 9090 FM',
        'ar': 'راديو 9090',
        'url': 'https://9090video.mobtada.com/hls/stream.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Fairuz',
        'ar': 'فيروز',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx029/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Falastini TV',
        'ar': 'فلسطيني',
        'url': 'https://rp.tactivemedia.com/palestiniantv_source/live/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Ishtar TV',
        'ar': 'إشتار',
        'url': 'https://stream.ishtartv.com/live/iShtarHD/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Jordan Songs',
        'ar': 'أغاني الأردن',
        'url': 'https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Song/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Majid Al Mohandis',
        'ar': 'ماجد المهندس',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx019/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Melody FM Jordan',
        'ar': 'ميلودي إف إم',
        'url': 'https://cdn3.wowza.com/1/OVRrOWxXUEswS2Yv/eGVxSWZy/hls/live/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'MFM',
        'ar': 'إم إف إم',
        'url': 'https://hms.pfs.gdn/hms/v1/broadcast/hlmvmp2hfriode891/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Mohammed Abdo',
        'ar': 'محمد عبده',
        'url': 'https://d2ow8h651gs7dx.cloudfront.net/out/v1/371fb663da604e659a2fb99bf89d92d4/index.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Mosaique FM',
        'ar': 'موزاييك',
        'url': 'https://webcam.mosaiquefm.net/mosatv/_definst_/studio/playlist.m3u8?DVR',
        'group': 'Music',
    },
    {
        'name': 'Nogoum FM TV',
        'ar': 'نجوم إف إم',
        'url': 'https://nogoumtv.nrpstream.com/hls/stream.m3u8',
        'group': 'Music',
    },
    {
        'name': 'One TV',
        'ar': 'وان تي في',
        'url': 'https://hms.pfs.gdn/v1/broadcast/one/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'One FM',
        'ar': 'وان إف إم',
        'url': 'https://hms.pfs.gdn/v1/broadcast/onefm/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Panorama FM',
        'ar': 'بانوراما إف إم',
        'url': 'https://d6izdil55uftn.cloudfront.net/out/v1/0a06d1d6377c47edbd48721ed724bd08/index.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Rabeh Saqer',
        'ar': 'رابح صقر',
        'url': 'https://shd-amg-fast.edgenextcdn.net/tx004/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Rashid AlMajed',
        'ar': 'راشد الماجد',
        'url': 'https://dphwv2ufgnfsq.cloudfront.net/out/v1/59cd80dfe93a479eb8b4d79bc6f225ca/index.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Abdulmajeed Abdullah',
        'ar': 'عبدالمجيد عبدالله',
        'url': 'https://d2hng5r56zpsbw.cloudfront.net/out/v1/9c4c990f44bb4767bb46271f326dd574/index.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Tarab',
        'ar': 'طرب',
        'url': 'https://shd-amg-fast-btpls.shahid.net/tx002/playlist.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Rotana Radio Jordan',
        'ar': 'روتانا راديو الأردن',
        'url': 'http://45.63.116.205/hls/stream1.m3u8',
        'group': 'Music',
    },
    {
        'name': 'Rotana Tarab Jordan',
        'ar': 'روتانا طرب الأردن',
        'url': 'http://45.63.116.205/hls3/stream1.m3u8',
        'group': 'Music',
    },
]


# ==============================================================================
# YOUTUBE DRAMA CONTENT
# Requires plugin.video.youtube addon (installed, enable when TV is on)
# ==============================================================================

YOUTUBE_CONTENT = [
    # --- Syrian Drama YouTube Channels ---
    {
        'name': 'DRAMA SYRIA — Syrian Drama Channel',
        'ar': 'قناة الدراما السورية',
        'yt_type': 'channel',
        'yt_id': 'UCCT9Zgk6Ig1tdJ0JlpzV5hg',
        'group': 'YouTube: Syrian Drama',
    },
    {
        'name': 'Comnix Drama — Syrian Drama & Movies',
        'ar': 'كومنكس دراما',
        'yt_type': 'channel',
        'yt_id': 'UCXUZe359JLMR6grJ0MVjiUg',
        'group': 'YouTube: Syrian Drama',
    },
    {
        'name': 'Bab Al Hara — All Seasons',
        'ar': 'باب الحارة جميع الأجزاء',
        'yt_type': 'channel',
        'yt_id': 'UCN1gDD9K5rRy5In2zRXuUGw',
        'group': 'YouTube: Syrian Drama',
    },
    {
        'name': 'Bab Al Hara — Complete Playlist (All Seasons 1-13)',
        'ar': 'باب الحارة قائمة كاملة',
        'yt_type': 'playlist',
        'yt_id': 'PLKo0VT6EZQVqwvSKTyukwdjLImUvEIgcQ',
        'group': 'YouTube: Syrian Drama',
    },
    {
        'name': 'Bab Al Hara Season 1 — Full Playlist',
        'ar': 'باب الحارة الجزء الأول',
        'yt_type': 'playlist',
        'yt_id': 'PL-DAUrBJxlftTNBWnWYuZxuUlIcZ1bBiz',
        'group': 'YouTube: Syrian Drama',
    },
    {
        'name': 'Best New Syrian Series — Playlist',
        'ar': 'أفضل مسلسلات سورية جديدة',
        'yt_type': 'playlist',
        'yt_id': 'PL6wUIyXvhb5Hs3oPD_oS0DJFLxGH3om96',
        'group': 'YouTube: Syrian Drama',
    },
    # --- Lebanese/Egyptian Drama YouTube Channels ---
    {
        'name': 'Media Revolution Seven — Lebanese & Egyptian Drama',
        'ar': 'ميديا ريفولوشن سبعة',
        'yt_type': 'channel',
        'yt_id': 'UC-ZvnB6NIypZO6H6PvXdOXw',
        'group': 'YouTube: Lebanese & Egyptian Drama',
    },
    {
        'name': 'LBCI Lebanon — Official Channel',
        'ar': 'إل بي سي لبنان',
        'yt_type': 'channel',
        'yt_id': 'UCpE6gpKewomi17XDyPfpFjA',
        'group': 'YouTube: Lebanese & Egyptian Drama',
    },
    {
        'name': 'Best Lebanese Series — Channel',
        'ar': 'أفضل المسلسلات اللبنانية',
        'yt_type': 'channel',
        'yt_id': 'UCDfoRdAmUlJLx2E_IBERPmA',
        'group': 'YouTube: Lebanese & Egyptian Drama',
    },
]


# ==============================================================================
# URL BUILDER
# ==============================================================================

def build_url(query):
    return sys.argv[0] + '?' + urllib.parse.urlencode(query)


# ==============================================================================
# KODI MENU FUNCTIONS
# ==============================================================================

def show_main_menu():
    """Main menu: Live TV categories + YouTube + About"""
    groups = {}
    for ch in LIVE_CHANNELS:
        g = ch['group']
        if g not in groups:
            groups[g] = 0
        groups[g] += 1

    yt_groups = {}
    for item in YOUTUBE_CONTENT:
        g = item['group']
        if g not in yt_groups:
            yt_groups[g] = 0
        yt_groups[g] += 1

    group_labels = {
        'Syrian': '🇸🇾 Syrian Channels',
        'Lebanese': '🇱🇧 Lebanese Channels',
        'Egyptian': '🇪🇬 Egyptian Channels',
        'Iraq': '🇮🇶 Iraqi Channels',
        'Jordan': '🇯🇴 Jordan Channels',
        'Arabic Drama': '🎬 Arabic Drama & Movies',
        'Music': '🎵 Arabic Music Video Channels',
    }

    group_order = ['Syrian', 'Lebanese', 'Egyptian', 'Arabic Drama', 'Iraq', 'Jordan', 'Music']

    for g in group_order:
        if g not in groups:
            continue
        label = group_labels.get(g, g)
        li = xbmcgui.ListItem(f'{label}  ({groups[g]} channels)')
        li.setInfo('video', {'plot': f'{groups[g]} live channels'})
        url = build_url({'mode': 'live_group', 'group': g})
        xbmcplugin.addDirectoryItem(addon_handle, url, li, isFolder=True)

    # YouTube sections
    yt_labels = {
        'YouTube: Syrian Drama': '📺 YouTube: Syrian Drama Series',
        'YouTube: Lebanese & Egyptian Drama': '📺 YouTube: Lebanese & Egyptian Drama',
    }
    for g in sorted(yt_groups.keys()):
        label = yt_labels.get(g, g)
        li = xbmcgui.ListItem(f'{label}  ({yt_groups[g]} items)')
        li.setInfo('video', {'plot': f'{yt_groups[g]} YouTube channels/playlists'})
        url = build_url({'mode': 'yt_group', 'group': g})
        xbmcplugin.addDirectoryItem(addon_handle, url, li, isFolder=True)

    # About
    li = xbmcgui.ListItem('ℹ️  About')
    li.setInfo('video', {'plot': 'Arabic Shows addon — made with love for Walaa'})
    url = build_url({'mode': 'about'})
    xbmcplugin.addDirectoryItem(addon_handle, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)


def show_live_group(group_name):
    """Show channels in a specific group"""
    for idx, ch in enumerate(LIVE_CHANNELS):
        if ch['group'] == group_name:
            li = xbmcgui.ListItem(ch['name'])
            li.setInfo('video', {'title': ch['name'], 'plot': ch.get('ar', '')})
            li.setProperty('IsPlayable', 'true')
            url = build_url({'mode': 'play_live', 'idx': str(idx)})
            xbmcplugin.addDirectoryItem(addon_handle, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)


def play_live_stream(idx):
    """Play a live HLS stream by channel index"""
    ch = LIVE_CHANNELS[int(idx)]
    stream_url = ch['url']
    name = ch['name']
    xbmc.log(f'[arabicshows] Playing: {name} - {stream_url[:80]}', xbmc.LOGINFO)
    item = xbmcgui.ListItem(label=name, path=stream_url)
    item.setInfo('video', {'title': name})
    item.setMimeType('application/x-mpegURL')
    item.setContentLookup(False)
    # HLS needs an inputstream addon. Try inputstream.ffmpegdirect (installed on this Kodi)
    # and fall back to inputstream.adaptive if available.
    item.setProperty('inputstream', 'inputstream.ffmpegdirect')
    item.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
    xbmcplugin.setResolvedUrl(addon_handle, True, item)


def show_yt_group(group_name):
    """Show YouTube channels/playlists in a group"""
    for idx, item in enumerate(YOUTUBE_CONTENT):
        if item['group'] == group_name:
            li = xbmcgui.ListItem(item['name'])
            desc = f"YouTube {'Channel' if item['yt_type'] == 'channel' else 'Playlist'} — {item.get('ar', '')}"
            li.setInfo('video', {'title': item['name'], 'plot': desc})
            li.setProperty('IsPlayable', 'false')
            url = build_url({'mode': 'open_yt', 'idx': str(idx)})
            xbmcplugin.addDirectoryItem(addon_handle, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)


def open_youtube(item):
    """Open a YouTube channel or playlist in the YouTube Kodi addon"""
    yt_type = item['yt_type']
    yt_id = item['yt_id']

    if yt_type == 'channel':
        yt_url = f'plugin://plugin.video.youtube/channel/{yt_id}/'
    elif yt_type == 'playlist':
        yt_url = f'plugin://plugin.video.youtube/playlist/{yt_id}/'
    else:
        xbmcgui.Dialog().ok('Error', f'Unknown YouTube type: {yt_type}')
        return

    xbmc.log(f'[arabicshows] Opening YouTube: {yt_type}/{yt_id}', xbmc.LOGINFO)
    item_li = xbmcgui.ListItem(label=item['name'], path=yt_url)
    xbmcplugin.setResolvedUrl(addon_handle, True, item_li)


# ==============================================================================
# ROUTER
# ==============================================================================

def router():
    args = urllib.parse.parse_qs(sys.argv[2][1:])
    mode = args.get('mode', [None])[0]

    if mode is None:
        show_main_menu()
    elif mode == 'live_group':
        show_live_group(args.get('group', [''])[0])
    elif mode == 'play_live':
        play_live_stream(args.get('idx', ['0'])[0])
    elif mode == 'yt_group':
        show_yt_group(args.get('group', [''])[0])
    elif mode == 'open_yt':
        idx = int(args.get('idx', ['0'])[0])
        if idx < len(YOUTUBE_CONTENT):
            open_youtube(YOUTUBE_CONTENT[idx])
        else:
            xbmcgui.Dialog().ok('Error', 'Invalid YouTube item index')
    elif mode == 'about':
        total = len(LIVE_CHANNELS)
        total_yt = len(YOUTUBE_CONTENT)
        xbmcgui.Dialog().ok(
            'Arabic Shows',
            f'Arabic Shows addon v1.0.6\n\n'
            f'Made with love for Walaa <3\n\n'
            f'{total} live Arabic TV channels:\n'
            f'  Syrian: Al-Souriya, Syria TV, Halab Today, Al Mayadeen,\n'
            f'          Bab Al Hara, Althania, Alikhbaria, Damascus Radio\n'
            f'  Lebanese: MTV, LBC, Al Jadeed, OTV, Future, VDL, Maraya,\n'
            f'            Al Manar\n'
            f'  Egyptian: MBC Masr, MBC 1 Egypt, Al Masriyah, CBC Sofra,\n'
            f'            Mekameleen, MBC Masr 2/USA\n'
            f'  Drama: MBC Drama, MBC+ Drama, CBC Drama, Roya, Jordan,\n'
            f'         MBC 1/4/5, MBC Iraq, MBC Mood, Aflam, Spacetoon,\n'
            f'         Ajyal, and more\n'
            f'  Iraqi: Al Iraqia, Al Iraqia News/Sport, Alhurra, Iraq Future\n'
            f'  Jordan: Jordan Satellite, Archive, Kitchen, Tourism, Roya Kids\n'
            f'  Music: Aghani, Arabica, Fairuz, Mohammed Abdo, Rotana, and more\n\n'
            f'{total_yt} YouTube drama channels/playlists:\n'
            f'  Syrian: DRAMA SYRIA, Comnix, Bab Al Hara (all seasons)\n'
            f'  Lebanese/Egyptian: Media Revolution, LBCI, Best Lebanese\n\n'
            f'YouTube requires plugin.video.youtube addon enabled.'
        )
    else:
        show_main_menu()


if __name__ == '__main__':
    router()