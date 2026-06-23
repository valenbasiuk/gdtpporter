# esto existe por una sola razon: que no vuelva a pasar lo que paso con
# los pinchos de WespTP.
#
# GD tiene dos sheets que se confunden facil:
#   - GJ_GameSheet02 / 03 / 04 / Glow -> menu, UI, iconos. esto SI lo tocan
#     los texture packs.
#   - GJ_GameSheet (sin numero, ni "02" ni nada) -> el sheet in-game.
#     pinchos, bloques, orbes, decoraciones. la gran mayoria de los tps
#     (aunque digan "full pack" o lo que sea) NO tocan esto.
#
# la vez que portamos WespTP a mano, el GameSheet04 no tenia plist y para
# arreglarlo tambien copie un GJ_GameSheet vanilla de otro lado pensando
# que "ya que estamos, lo completo". error. ese archivo no es del pack,
# es el que ya trae instalado el juego del usuario, y mi copia no
# coincidia bien con esa version puntual de GD. resultado: los pinchos
# (que antes andaban bien con el GameSheet del juego real) se rompieron.
#
# la solucion fue sacar ese archivo. y esto de aca es para que no se
# repita: ningun modulo de este programa puede escribir GJ_GameSheet
# (con o sin -hd/-uhd) bajo ninguna circunstancia, ni aunque la carpeta
# de --reference tenga uno.

from pathlib import Path

# ojo: GJ_GameSheet02, 03, 04, Glow NO entran aca. esos son archivos de
# menu que los packs si personalizan, no hay drama en tocarlos.
PROTECTED_BASENAMES = {"GJ_GameSheet", "GJ_GameSheet-hd", "GJ_GameSheet-uhd"}


class ProtectedFileError(RuntimeError):
    pass


def assert_not_protected(path: Path) -> None:
    # path.stem = nombre del archivo sin la extension
    stem = path.stem
    if stem in PROTECTED_BASENAMES:
        raise ProtectedFileError(
            f"no se va a escribir {path.name}: es el sheet in-game. el "
            "juego del usuario ya tiene su propia copia correcta de este "
            "archivo y no hay forma de garantizar que la nuestra coincida "
            "con su version de GD. si en serio este pack puntual modifica "
            "sprites in-game, hay que copiar ese archivo a mano, no asi."
        )


def filter_out_protected(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """separa una lista de paths candidatos en (los que se pueden escribir, los que no)"""
    safe, rejected = [], []
    for p in paths:
        if p.stem in PROTECTED_BASENAMES:
            rejected.append(p)
        else:
            safe.append(p)
    return safe, rejected
