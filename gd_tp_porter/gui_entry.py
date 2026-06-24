# esto es lo que se compila a gd-tp-porter.exe con pyinstaller. pensado
# para alguien que JAMAS abrio una terminal: o le arrastra el .rar/.zip
# encima al .exe (windows pasa la ruta como argv[1]), o le hace doble
# click sin nada y le preguntamos la ruta por texto.
#
# OJO: esto no es el CLI (__main__.py). el CLI es para gente que ya sabe
# usar la consola y quiere las opciones de --reference, --zip, etc a mano.
# esto de aca es la version sin vueltas: agarra el archivo, lo portea con
# la referencia vanilla que viene empaquetada adentro del exe, y te dice
# donde quedo.

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from .extract import ExtractionError
from .porter import port_input


def _ruta_referencia_empaquetada() -> Path:
    """
    donde esta la carpeta vanilla_reference/, tanto corriendo desde
    código fuente como ya compilado con pyinstaller (que descomprime
    todo en una carpeta temporal y la deja en sys._MEIPASS).
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    if hasattr(sys, "_MEIPASS"):
        return base / "gd_tp_porter" / "vanilla_reference"
    return Path(__file__).parent / "vanilla_reference"


def _pausar_antes_de_cerrar() -> None:
    # si lo abriste con doble click, la consola se cierra sola apenas
    # termina el programa y no llegas a leer nada. esto la deja abierta
    # hasta que apretes algo.
    try:
        input("\npresiona ENTER para cerrar...")
    except (EOFError, KeyboardInterrupt):
        pass


def _pedir_archivo_por_consola() -> Path:
    print("=" * 60)
    print(" gd-tp-porter -- portea texture packs de GD 2.1 a 2.2")
    print("=" * 60)
    print()
    print("arrastra tu .rar/.zip a esta ventana (o escribi la ruta a mano)")
    print("y apreta ENTER:")
    print()
    while True:
        raw = input("> ").strip()
        # cuando arrastras un archivo a la consola de windows, a veces
        # viene entre comillas. se las sacamos si estan.
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        path = Path(raw)
        if path.exists():
            return path
        print(f"no encuentro '{raw}', probá de nuevo (o arrastrá el archivo de nuevo)")


def run() -> int:
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        if not input_path.exists():
            print(f"error: no existe {input_path}")
            _pausar_antes_de_cerrar()
            return 1
    else:
        input_path = _pedir_archivo_por_consola()

    referencia = _ruta_referencia_empaquetada()
    if not referencia.is_dir():
        referencia = None  # por si el .exe se armo sin la carpeta, que no rompa todo

    print()
    print(f"portenado {input_path.name} ...")
    print()

    try:
        output_dir, report, _ = port_input(
            input_path,
            reference_dir=referencia,
            make_zip=True,
        )
    except ExtractionError as e:
        print(f"error: {e}")
        _pausar_antes_de_cerrar()
        return 1
    except OSError as e:
        # lo mas probable: no se puede escribir al lado del archivo
        # original (ej viene de una carpeta protegida, o read-only).
        # le pedimos una carpeta de salida a mano en vez de explotar.
        print(f"no pude crear la carpeta de salida ahi al lado ({e}).")
        carpeta = input("decime una carpeta donde si pueda escribir (ej Escritorio): ").strip().strip('"')
        try:
            output_dir, report, _ = port_input(
                input_path,
                output_dir=Path(carpeta) / f"{input_path.stem}_2.2",
                reference_dir=referencia,
                make_zip=True,
            )
        except Exception:
            print("sigue sin andar. mandanos este error completo:")
            print()
            traceback.print_exc()
            _pausar_antes_de_cerrar()
            return 1
    except Exception:
        # cualquier otra cosa que explote, mostramos el traceback completo
        # porque sino el usuario nos manda un screenshot de la ventana
        # que se cerro y no podemos hacer nada con eso
        print("algo se rompio. mandanos este error completo:")
        print()
        traceback.print_exc()
        _pausar_antes_de_cerrar()
        return 1

    print(report.render())
    print()
    print(f"listo! el pack ya portado a 2.2 quedo en:\n  {output_dir}")
    print()
    print(f"tambien lo deje zipeado, listo para copiar a tu carpeta Resources:\n  {output_dir}.zip")

    _pausar_antes_de_cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
