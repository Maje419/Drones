from typing import TypedDict

class Vejnavn(TypedDict):
    kode: str
    navn: str

class Postnummer(TypedDict):
    nr: str
    navn: str

class Kommune(TypedDict):
    kode: str

class Etrs89koordinat(TypedDict):
    oest: str
    nord: str

class Wgs84koordinat(TypedDict):
    bredde: str
    laengde: str

class Tjenesteart(TypedDict):
    id: str
    navn: str

class Teknologi(TypedDict):
    id: str
    navn: str

class Mast(TypedDict):
    vejnavn: Vejnavn
    husnr: str
    postnummer: Postnummer
    kommune: Kommune
    idriftsaettelsesdato: str
    forventet_idriftsaettelsesdato: str
    etrs89koordinat: Etrs89koordinat
    wgs84koordinat: Wgs84koordinat
    tjenesteart: Tjenesteart
    teknologi: Teknologi
    unik_station_navn: str
    radius_i_meter: str
    frekvensbaand: str
