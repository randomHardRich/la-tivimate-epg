# US + Los Angeles EPG for TiviMate

`build_epg.py` makes `epg.xml.gz`: 253 channels (27 LA stations, 3 LA regional, 223 national).
Listings reach about 2.5 days ahead, so rebuild it daily.

## Rebuild by hand

```bash
python3 build_epg.py --output epg.xml.gz
```

## Host it automatically (free)

1. Push this folder to a public GitHub repository.
2. In the repository's Actions tab, run **Build EPG** once. It then runs daily.
3. Your guide URL is:
   `https://raw.githubusercontent.com/randomHardRich/la-tivimate-epg/guide/epg.xml.gz`

## Add it to TiviMate

1. Go to Settings > EPG and add an EPG source, using the URL above.
2. Update the EPG, then check a few channels such as KABC, ESPN and TNT.
3. For any channel with no guide, open its channel settings and pick the guide channel by hand.

## Channel IDs

Match these in your playlist's `tvg-id` for automatic mapping:

- LA stations use the call sign: `KABC.us`, `KCBS.us`, `KNBC.us`, `KTTV.us`
- National channels use the name: `ESPN.us`, `TNT.us`
- West feeds add `West`: `TNT.West.us`

## Change the channels

Edit `LA_LOCALS`, `LA_REGIONAL` or `NATIONAL` in `build_epg.py`. Names must match the source
guide exactly. Any that find no listings are printed when you build.
