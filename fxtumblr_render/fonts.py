# SPDX-License-Identifier: MIT
"""Code for managing fonts."""

#: Mapping of font names to URLs.
FONT_URLS: dict[str, str] = {
    # Main font
    "favorit-85": "https://assets.tumblr.com/pop/src/assets/fonts/favorit/favorit-85-cf2f6136.woff2",
    "favorit-85-italic": "https://assets.tumblr.com/pop/src/assets/fonts/favorit/favorit-85-italic-b336f07b.woff2",
    "favorit-medium": "https://assets.tumblr.com/pop/src/assets/fonts/favorit/favorit-medium-fbc7316f.woff2",
    "favorit-regular": "https://assets.tumblr.com/pop/src/assets/fonts/favorit/favorit-regular-52013406.woff2",
    "favorit-bold": "https://assets.tumblr.com/pop/src/assets/fonts/favorit/favorit-bold-014cc624.woff2",
    # "Lucille" paragraph style
    "fairwater-regular": "https://assets.tumblr.com/pop/src/assets/fonts/fairwater/fairwater-regular-940c9e87.woff2",
    # Profile fonts
    "1785glcbaskerville-regular": "https://assets.tumblr.com/pop/src/assets/fonts/1785glcbaskerville/1785glcbaskerville-regular-aab85583.woff",
    "alternategothic-regular": "https://assets.tumblr.com/pop/src/assets/fonts/alternategothic/alternategothic-regular-2e1c7639.woff",
    "arquitecta-book": "https://assets.tumblr.com/pop/src/assets/fonts/arquitecta/arquitecta-book-06f16615.woff",
    "arquitecta-bold": "https://assets.tumblr.com/pop/src/assets/fonts/arquitecta/arquitecta-bold-8f86d409.woff",
    "avalon-book": "https://assets.tumblr.com/pop/src/assets/fonts/avalon/avalon-book-9556d123.woff",
    "avalon-bold": "https://assets.tumblr.com/pop/src/assets/fonts/avalon/avalon-bold-8414808d.woff",
    "bodonirecutfs-regular": "https://assets.tumblr.com/pop/src/assets/fonts/bodonirecutfs/bodonirecutfs-regular-23705890.woff",
    "bodonirecutfs-demi": "https://assets.tumblr.com/pop/src/assets/fonts/bodonirecutfs/bodonirecutfs-demi-32ef73d2.woff",
    "bookmania-regular": "https://assets.tumblr.com/pop/src/assets/fonts/bookmania/bookmania-regular-cbfbe4f0.woff",
    "bookmania-bold": "https://assets.tumblr.com/pop/src/assets/fonts/bookmania/bookmania-bold-33dbd998.woff",
    "brutaltype-regular": "https://assets.tumblr.com/pop/src/assets/fonts/brutaltype/brutaltype-regular-26efc686.woff",
    "brutaltype-bold": "https://assets.tumblr.com/pop/src/assets/fonts/brutaltype/brutaltype-bold-3bb826ab.woff",
    "calluna-regular": "https://assets.tumblr.com/pop/src/assets/fonts/calluna/calluna-regular-3e7aea87.woff",
    "calluna-black": "https://assets.tumblr.com/pop/src/assets/fonts/calluna/calluna-black-74c26895.woff",
    "callunasans-regular": "https://assets.tumblr.com/pop/src/assets/fonts/callunasans/callunasans-regular-a37dd86e.woff",
    "callunasans-black": "https://assets.tumblr.com/pop/src/assets/fonts/callunasans/callunasans-black-5078c01e.woff",
    "capita-regular": "https://assets.tumblr.com/pop/src/assets/fonts/capita/capita-regular-6bb9a611.woff",
    "capita-bold": "https://assets.tumblr.com/pop/src/assets/fonts/capita/capita-bold-9115761b.woff",
    "caslonfs-book": "https://assets.tumblr.com/pop/src/assets/fonts/caslonfs/caslonfs-book-8247d3a4.woff",
    "caslonfs-bold": "https://assets.tumblr.com/pop/src/assets/fonts/caslonfs/caslonfs-bold-6c16fa21.woff",
    "clarendontextpro-regular": "https://assets.tumblr.com/pop/src/assets/fonts/clarendontextpro/clarendontextpro-regular-fd1c116e.woff",
    "clarendontextpro-bold": "https://assets.tumblr.com/pop/src/assets/fonts/clarendontextpro/clarendontextpro-bold-e4c3ed42.woff",
    "clearface-regular": "https://assets.tumblr.com/pop/src/assets/fonts/clearface/clearface-regular-87a9303a.woff",
    "clearface-black": "https://assets.tumblr.com/pop/src/assets/fonts/clearface/clearface-black-96c8de77.woff",
    "garamondclassicfs-regular": "https://assets.tumblr.com/pop/src/assets/fonts/garamondclassicfs/garamondclassicfs-regular-b78d391d.woff",
    "garamondclassicfs-heavy": "https://assets.tumblr.com/pop/src/assets/fonts/garamondclassicfs/garamondclassicfs-heavy-d0f81d74.woff",
    "gibson-regular": "https://assets.tumblr.com/pop/src/assets/fonts/gibson/gibson-regular-359608a5.woff",
    "gibson-semibold": "https://assets.tumblr.com/pop/src/assets/fonts/gibson/gibson-semibold-ed60525b.woff",
    "grumpyblack48": "https://assets.tumblr.com/pop/src/assets/fonts/grumpyblack48/grumpyblack48-ded7f4ab.woff",
    "lorimeno2-medium": "https://assets.tumblr.com/pop/src/assets/fonts/lorimerno2/lorimerno2-medium-53352f06.woff",
    "lorimeno2-semibold": "https://assets.tumblr.com/pop/src/assets/fonts/lorimerno2/lorimerno2-semibold-47aa4745.woff",
    "newsgothicfs-book": "https://assets.tumblr.com/pop/src/assets/fonts/newsgothicfs/newsgothicfs-book-097e7a77.woff",
    "newsgothicfs-bold": "https://assets.tumblr.com/pop/src/assets/fonts/newsgothicfs/newsgothicfs-bold-f7a99779.woff",
    "prattpro-regular": "https://assets.tumblr.com/pop/src/assets/fonts/prattpro/prattpro-regular-8ac820d1.woff",
    "prattpro-bold": "https://assets.tumblr.com/pop/src/assets/fonts/prattpro/prattpro-bold-ea47439e.woff",
    "quadrat-regular": "https://assets.tumblr.com/pop/src/assets/fonts/quadrat/quadrat-regular-c826f4a4.woff",
    "quadrat-serial": "https://assets.tumblr.com/pop/src/assets/fonts/quadrat/quadrat-serial-38dacd37.woff",
    "sofiapro-regular": "https://assets.tumblr.com/pop/src/assets/fonts/sofiapro/sofiapro-regular-3c08c43f.woff",
    "sofiapro-bold": "https://assets.tumblr.com/pop/src/assets/fonts/sofiapro/sofiapro-bold-9edfc161.woff",
    "spade": "https://assets.tumblr.com/pop/src/assets/fonts/spade/spade-03f6f853.woff",
    "squareserif-book": "https://assets.tumblr.com/pop/src/assets/fonts/squareserif/squareserif-book-c0c88eb2.woff",
    "squareserif-demi": "https://assets.tumblr.com/pop/src/assets/fonts/squareserif/squareserif-demi-0eceb357.woff",
    "streetscript": "https://assets.tumblr.com/pop/src/assets/fonts/streetscript/streetscript-eaf42fba.woff",
    "typewriterfs-regular": "https://assets.tumblr.com/pop/src/assets/fonts/typewriterfs/typewriterfs-regular-8f4e158c.woff",
    "typewriterfs-bold": "https://assets.tumblr.com/pop/src/assets/fonts/typewriterfs/typewriterfs-bold-a2c59cec.woff",
    "ziclets": "https://assets.tumblr.com/pop/src/assets/fonts/ziclets/ziclets-86a7d8eb.woff",
}


def get_font_uri(font_name: str) -> str:
    """
    Get an URL pointing to the font.

    :param font_name: Name of font.
    :returns: URL to font.
    :raises KeyError: if the font is not in the list.
    """

    return FONT_URLS[font_name]
