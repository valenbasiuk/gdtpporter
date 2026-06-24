# wrapper de arranque solo para pyinstaller. el problema: gui_entry.py
# vive ADENTRO del paquete y usa imports relativos (from .extract import
# ...), pero pyinstaller lo corre como si fuera un script suelto y eso
# rompe los imports relativos. esto de aca esta afuera del paquete y
# hace el import absoluto, asi que no tiene ese problema.
#
# no es para correr a mano -- es el "script" que le pasamos a pyinstaller
# (ver gd-tp-porter.spec / el workflow de build).

from gd_tp_porter.gui_entry import run

if __name__ == "__main__":
    raise SystemExit(run())
