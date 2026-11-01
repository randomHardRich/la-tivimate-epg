#!/usr/bin/env python3
"""Build a compact XMLTV guide (epg.xml.gz) of US channels plus Los Angeles locals.

Listings come from epgshare01's US national and US locals guides (about 3 days ahead).
epg.pw also carries these channels, but its timestamps run 8 hours late, so it is not used.

Usage:  python3 build_epg.py [--output epg.xml.gz] [--source FILE ...]
Only the Python standard library is needed.
"""
import argparse
import gzip
import os
import re
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

SOURCE_URLS = [
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US_LOCALS1.xml.gz",
]
MIN_CHANNELS_WITH_LISTINGS = 150  # below this, keep the previous guide instead

# Source station name, brand shown in TiviMate, extra names people's playlists use.
LA_LOCALS = [
    ("KCBS-DT", "CBS 2 Los Angeles", ["CBS Los Angeles", "CBS LA"]),
    ("KNBC-DT", "NBC 4 Los Angeles", ["NBC Los Angeles", "NBC LA", "NBC4"]),
    ("KTLA-DT", "KTLA 5 Los Angeles", ["KTLA 5", "CW Los Angeles"]),
    ("KABC-DT", "ABC 7 Los Angeles", ["ABC Los Angeles", "ABC LA", "ABC7"]),
    ("KCAL-DT", "KCAL 9 Los Angeles", ["KCAL 9", "KCAL News"]),
    ("KTTV-DT", "FOX 11 Los Angeles", ["FOX Los Angeles", "FOX LA", "Fox 11"]),
    ("KCOP-DT", "MyNetworkTV 13 Los Angeles", ["KCOP 13", "My 13", "MyNetworkTV Los Angeles", "MY13", "MY13 (KCOP)", "US: MY13 (KCOP) Los Angeles, CA", "US: MY13 (KCOP) Los Angeles"]),
    ("KSCI-DT", "KSCI 18 Los Angeles", []),
    ("KCET-DT", "KCET 28 Los Angeles", ["PBS SoCal Plus", "KCET"]),
    ("KPXN-DT", "ION 30 Los Angeles", ["ION Los Angeles"]),
    ("KVMD-DT", "KVMD 31 Los Angeles", []),
    ("KMEX-DT", "Univision 34 Los Angeles", ["Univision Los Angeles"]),
    ("KTBN-DT", "TBN 40 Los Angeles", ["TBN Los Angeles"]),
    ("KXLA-DT", "KXLA 44 Los Angeles", []),
    ("KFTR-DT", "UniMas 46 Los Angeles", ["UniMas Los Angeles"]),
    ("KOCE-DT", "PBS SoCal 50", ["PBS Los Angeles", "PBS LA", "PBS SoCal"]),
    ("KVEA-DT", "Telemundo 52 Los Angeles", ["Telemundo Los Angeles"]),
    ("KAZA-DT", "KAZA 54 Los Angeles", []),
    ("KDOC-DT", "KDOC 56 Los Angeles", []),
    ("KJLA-DT", "KJLA 57 Los Angeles", []),
    ("KLCS-DT", "KLCS 58 Los Angeles", ["PBS KLCS"]),
    ("KRCA-DT", "KRCA 62 Los Angeles", []),
    ("KBEH-DT", "KBEH 63 Los Angeles", []),
    ("KILM-DT", "KILM Los Angeles", []),
    ("KHIZ-LD", "KHIZ Los Angeles", []),
    ("KNLA-CD", "KNLA Los Angeles", []),
    ("KPOM-CD", "KPOM Los Angeles", []),
]

# LA-area cable and sports channels, by their exact name in the source guide.
LA_REGIONAL = {
    "Spectrum News 1 - SO CAL - STVA": "Spectrum News 1 SoCal",
    "Spectrum SportsNet Lakers HD": "Spectrum SportsNet",
    "Spectrum SportsNet LA Dodgers HD": "SportsNet LA",
}

# Exact source names. "(Pacific)" feeds are listed so West streams get correct times.
NATIONAL = """
A and E HD East|ABC News Live|ACC Network|AMC HD|AXS TV|Animal Planet HD|Animal Planet HD (Pacific)
Antenna TV|BBC America HD|BBC News (North America) HD|BET HD|BET HD (Pacific)|BET Her
BUZZR Stream|BYU-TV|Big Ten Network HD|Bloomberg HD|Boomerang|Bounce TV|Bravo HD|Bravo (Pacific)
CMT HD|CNBC HD|CNN HD|CNN International|COZI TV|CSPAN|CSPAN2|CSPAN3
Cartoon Network HD|Cartoon Network (Pacific)|Catchy Comedy|Cinemax HD|Cinemax HD (Pacific)
Cleo TV HD|Comedy Central HD|Comedy Central HD (Pacific)|Comet|Comet (Pacific)|Cooking Channel HD
Court TV|Create|Crime and Investigation Network HD|DUCKTV|Dabl|Destination America HD
Discovery Channel HD|The Discovery Channel HD (Pacific)|Discovery Family Channel HD
Discovery Life Channel|Disney Channel HD|Disney Channel (Pacific)|Disney Junior HD
Disney Junior HD (Pacific)|Disney XD HD|Disney XD HD (Pacific)|E! Entertainment Television HD
ESPN Deportes HD|ESPN HD|ESPN2 HD|ESPNEWS HD|ESPNU HD|Estrella TV|Eternal Word Television Network
FS1 HD|FS2 HD|FX HD|FX HD (Pacific)|FX Movie Channel HD|FXX HD|FXX HD (Pacific)|FYI Channel HD
Food Network HD|Fox Business HD|Fox Deportes HD|Fox News Channel HD|Freeform HD|Freeform Pacific
Fuse HD|GOL TV|Galavision Cable Network HD|Galavision Cable Network HD (Pacific)
Game Show Network HD|Golf Channel HD|Great American Family HD|Grit
HBO East|HBO West|HBO2 HD|HBO2 HD (Pacific)|HBO Comedy HD|HBO Drama|HBO Hits|HBO Latino HD
HBO Movies|HBO Signature HD|HBO Zone HD|HDNet Movies|HLN HD|HSN Home Shopping Network HD
Hallmark Channel HD|Hallmark Family|Hallmark Mystery HD|Heroes and Icons Network SD|History HD
Home and Garden Television HD|Home and Garden Television HD (Pacific)|IFC HD|INSP HD
ION Television HD|Investigation Discovery HD|Investigation Discovery HD (Pacific)|LMN HD|Laff
Law and Crime|Lifetime HD|Logo|MGM+ HD|MGM+ Hits HD|MGM+ Marquee HD|MOTORTREND HD|MS NOW HD
MTV - Music Television HD|MTV - Music Television HD (Pacific)|MTV2: Music Television HD|MTV Classic
Magnolia Network HD|Me TV Network|MeTV Toons|Movies!|NBC Sports California HD|NewsNation
National Geographic HD|National Geographic HD (Pacific)|National Geographic Wild HD|Newsmax TV HD
Nick Jr HD|Nickelodeon HD|Nickelodeon (Pacific)|Nicktoons|One America News Network HD
Oprah Winfrey Network HD|Oprah Winfrey Network (Pacific A Feed)|Outdoor Channel HD
Outside Television HD|Ovation HD|Oxygen True Crime HD|PBS KIDS HD|POP HD|Paramount Network HD
Paramount+ with Showtime HD|Paramount+ with Showtime HD (Pacific)|QVC HD|RFD TV HD|ReelzChannel HD
Revolt HD|SEC Network HD|Science Channel HD|Scripps News|Showtime 2 HD|Showtime Extreme HD
Showtime Familyzone HD|Showtime Next HD|Showtime Showcase HD|Showtime Women HD|Smithsonian HD Network
Sony Movie Channel HD|Sportsman Channel|Start TV Network|Starz HD|Starz HD (Pacific)|Starz Cinema HD
Starz Comedy HD|Starz Edge HD|Starz Encore HD|Starz Encore (Pacific)|Starz Kids HD|Starz in Black HD
SundanceTV HD|Syfy HD|Syfy HD (Pacific)|TBS HD|TBS HD (Pacific)|TLC HD (US)|TLC HD (Pacific)
TNT HD|TNT HD (Pacific)|TUDN|TV Land HD|TV Land HD (Pacific)|TV ONE HD|Teen Nick
Telemundo Satellite Feed|Telemundo Satellite Feed Pacific|Tennis Channel HD|The Cowboy Channel
The Movie Channel HD|The Movie Channel (Pacific)|The Travel Channel HD|The Travel Channel HD (Pacific)
The Weather Channel HD|Trinity Broadcasting Network HD|Turner Classic Movies HD|UPtv
USA Network HD|USA Network HD (Pacific)|UniMas|UniMas HD (Pacific)|Univision Network HD
Univision Network (Pacific)|VH1 HD|WE tv HD|WORLD Channel|Weather Nation TV HD|beIN Sports USA HD
beIN Sports En Español HD|truTV HD|truTV HD (Pacific)|NFL Network HD|NFL RedZone HD|NBA TV HD
NHL Network HD|MLB Network HD
"""

BRAND_NAMES = {
    "A and E HD East": "A&E",
    "BBC News (North America) HD": "BBC News",
    "E! Entertainment Television HD": "E!",
    "Eternal Word Television Network": "EWTN",
    "Fox News Channel HD": "Fox News",
    "HSN Home Shopping Network HD": "HSN",
    "Heroes and Icons Network SD": "Heroes & Icons",
    "Home and Garden Television HD": "HGTV",
    "Home and Garden Television HD (Pacific)": "HGTV West",
    "Me TV Network": "MeTV",
    "MTV - Music Television HD": "MTV",
    "MTV - Music Television HD (Pacific)": "MTV West",
    "MTV2: Music Television HD": "MTV2",
    "Oprah Winfrey Network HD": "OWN",
    "Oprah Winfrey Network (Pacific A Feed)": "OWN West",
    "Turner Classic Movies HD": "TCM",
    "The Discovery Channel HD (Pacific)": "Discovery Channel West",
    "Telemundo Satellite Feed": "Telemundo",
    "Telemundo Satellite Feed Pacific": "Telemundo West",
    "Trinity Broadcasting Network HD": "TBN",
    "Paramount+ with Showtime HD": "Showtime",
    "Paramount+ with Showtime HD (Pacific)": "Showtime West",
    "HBO East": "HBO",
    "Freeform Pacific": "Freeform West",
    "UniMas HD (Pacific)": "UniMas West",
}


def brand_name(source_name):
    """'TNT HD (Pacific)' -> 'TNT West', 'ESPN HD' -> 'ESPN'."""
    if source_name in BRAND_NAMES:
        return BRAND_NAMES[source_name]
    name = re.sub(r"\s*\((Pacific|US)[^)]*\)", lambda m: " West" if m[1] == "Pacific" else "", source_name)
    return re.sub(r"\s+(HD|SD)\b", "", name).strip()


def channel_id(name):
    return re.sub(r"[^A-Za-z0-9]+", ".", name.replace("&", "and")).strip(".") + ".us"


def wanted_channels():
    """Return {source display name: (output id, [display names])}."""
    wanted = {}
    for station, brand, aliases in LA_LOCALS:
        call = station.split("-")[0]
        wanted[station] = (f"{call}.us", [brand, f"{call} {brand}", call, station, *aliases])
    for source, brand in LA_REGIONAL.items():
        wanted[source] = (channel_id(brand), [brand, source])
    for source in re.split(r"[|\n]", NATIONAL.strip()):
        brand = brand_name(source)
        names = [brand, source]
        if brand.endswith(" West"):
            names.append(brand[:-5] + " Pacific")
        wanted[source] = (channel_id(brand), list(dict.fromkeys(names)))
    return wanted


def download(url, directory):
    path = os.path.join(directory, url.rsplit("/", 1)[1])
    print(f"Downloading {url}", file=sys.stderr)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=300) as response, open(path, "wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    return path


def read_guide(path, wanted, seen):
    """Stream an XMLTV file, keeping the wanted channels not already in seen.

    Returns ({output id: icon url}, {output id: [programme xml strings]}).
    """
    icons, listings, ids = {}, {}, {}
    with gzip.open(path, "rb") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag == "channel":
                names = [(n.text or "").strip() for n in element.findall("display-name")]
                out_id = next((wanted[n][0] for n in names if n in wanted), None)
                if out_id and out_id not in seen and out_id not in icons:
                    ids[element.get("id")] = out_id
                    icon = element.find("icon")
                    icons[out_id] = icon.get("src", "") if icon is not None else ""
                element.clear()
            elif element.tag == "programme":
                out_id = ids.get(element.get("channel"))
                if out_id:
                    element.set("channel", out_id)
                    listings.setdefault(out_id, []).append(ET.tostring(element, encoding="unicode").strip())
                element.clear()
    return icons, listings


def write_guide(path, channels, icons, listings):
    temp = path + ".tmp"
    with gzip.open(temp, "wt", encoding="utf-8") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="build_epg.py">\n')
        for out_id, names in channels:
            out.write(f"  <channel id={quoteattr(out_id)}>\n")
            for name in names:
                out.write(f'    <display-name lang="en">{escape(name)}</display-name>\n')
            if icons.get(out_id):
                out.write(f"    <icon src={quoteattr(icons[out_id])} />\n")
            out.write("  </channel>\n")
        for out_id, _ in channels:
            for programme in listings.get(out_id, []):
                out.write(f"  {programme}\n")
        out.write("</tv>\n")
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="epg.xml.gz")
    parser.add_argument("--source", action="append", help="use this local XMLTV .gz instead of downloading")
    args = parser.parse_args()

    wanted = wanted_channels()
    icons, listings = {}, {}
    with tempfile.TemporaryDirectory() as work:
        for source in args.source or [download(url, work) for url in SOURCE_URLS]:
            new_icons, new_listings = read_guide(source, wanted, icons)
            icons.update(new_icons)
            listings.update(new_listings)

    channels = [(out_id, names) for out_id, names in wanted.values() if out_id in listings]
    absent = [source for source, (out_id, _) in wanted.items() if out_id not in listings]
    programmes = sum(len(v) for v in listings.values())
    print(f"{len(channels)} channels, {programmes} programmes", file=sys.stderr)
    if absent:
        print(f"No listings for: {', '.join(absent)}", file=sys.stderr)
    if len(channels) < MIN_CHANNELS_WITH_LISTINGS:
        sys.exit(f"Only {len(channels)} channels had listings; not replacing {args.output}")
    write_guide(args.output, channels, icons, listings)
    print(f"Wrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
