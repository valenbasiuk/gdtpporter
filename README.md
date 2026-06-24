# gd-tp-porter

Portea texture packs de Geometry Dash de la era **2.1** para que anden bien
en **2.2**, sin tener que separar sheets de iconos a mano ni andar
cazando plists rotos.

Esto automatiza un proceso que normalmente se hace manualmente (o con un
script improvisado + mucho prueba y error): separar el sheet viejo de
iconos en los sheets individuales que pide 2.2, y arreglar varios bugs de
plist que aparecen en packs reales distribuidos por ahí.

## Descargar y usar (sin terminal)

Si no usas la consola, bajate el ejecutable de la
[página de Releases](../../releases) — el que dice `gd-tp-porter-windows.exe`
si usas Windows (la inmensa mayoría).

Le hacés doble click y te va a pedir la ruta del `.rar`/`.zip` de tu pack
(o se lo podes arrastrar directamente encima del .exe). Al toque te tira
una carpeta con el pack ya listo para 2.2, más un .zip para copiar directo
a tu carpeta `Resources`.

Este ejecutable ya trae adentro las coordenadas vanilla de Geometry Dash
para los sheets de menú (no el arte, solo las coordenadas — ver la sección
de abajo), así que arregla automáticamente cosas como el bug de
`GJ_GameSheet04` sin que tengas que conseguir nada aparte.

## Que hace

1. **Separa los iconos para 2.2.** Antes de 2.2, todos los iconos de
   player/ship/robot/spider/dart/bird vivian amontonados en
   `GJ_GameSheet02` (+ las variantes de glow en `GJ_GameSheetGlow`). 2.2 en
   cambio espera un sheet chiquito por cada icono, en `Resources/icons/`.
   esto hace esa separacion por vos, para las calidades que traiga el pack
   (`""`, `-hd`, `-uhd`).

2. **Arregla la corrupcion de plist conocida.** algunos packs distribuidos
   tienen un `<true/>`/`<false/>` de `textureRotated` que perdio el
   `<key>textureRotated</key>` de antes. eso es xml invalido y rompe el
   parseo (y el juego). se detecta y arregla solo.

3. **Arregla `metadata.size` viejo.** es puramente cosmetico -- no afecta
   como se ve nada -- pero varios packs tienen un valor que quedo de una
   exportacion anterior. se corrige por prolijidad.

4. **Detecta (y puede arreglar) sheets sin su `.plist`.** nos paso en la
   vida real con `GJ_GameSheet04` (el sheet de Hall of Fame, Daily, Weekly,
   Map Packs, Gauntlets, Featured, etc) -- algunos packs traen el `.png`
   sin ningun `.plist` al lado. sin ese descriptor, Cocos2d no tiene como
   saber donde cortar cada sprite, y la UI sale toda rota/recortada mal. si
   le pasas `--reference <carpeta_vanilla_2.2>` y el png del pack mide
   **exactamente lo mismo en pixeles** que el de la referencia, el programa
   le pide prestadas las coordenadas (no el arte) y reconstruye un plist
   que funciona. si las medidas no coinciden, se niega y te dice por que,
   en vez de adivinar.

5. **Nunca toca el sheet in-game.** ver mas abajo -- esta es la decision de
   diseño mas importante de toda la herramienta.

## Instalar (modo consola, para developers)

```bash
git clone https://github.com/<tu-usuario>/gd-tp-porter.git
cd gd-tp-porter
pip install -r requirements.txt
```

Para extraer `.rar` hace falta algun binario que lo entienda. El `unrar`
no-free anda de una; en debian/ubuntu el `unrar-free` por defecto solo
entiende RAR4 y **no** RAR5 (que es como vienen muchos packs). Si la
extraccion falla, instalá alguno de estos:

```bash
sudo apt install p7zip-full       # trae 7z, lee RAR5
sudo apt install libarchive-tools # trae bsdtar
```

El programa prueba primero con `rarfile`/`unrar` y si falla cae solo a
`7z`/`7za`/`bsdtar`.

## Uso por consola

```bash
# directo desde el archivo descargado:
python -m gd_tp_porter MiPack.rar

# y de paso te genera un .zip listo para compartir:
python -m gd_tp_porter MiPack.rar --zip

# si ya lo tenes extraido:
python -m gd_tp_porter ./MiPackCarpeta -o ./MiPackCarpeta_2.2

# para que ademas rellene los plists de menu que falten (GJ_GameSheet04,
# GauntletSheet, etc) usando coordenadas de una copia vanilla de 2.2:
python -m gd_tp_porter MiPack.rar --reference ./resources_vanilla_2.2
```

`python -m gd_tp_porter --help` para ver todas las opciones. cada corrida
te tira un reporte de exactamente que se cambio, que se salteo, y por que
-- nada pasa en silencio.

### De donde saco una carpeta para `--reference`

Cualquier copia legitima y sin modificar de la carpeta `Resources` de GD
2.2 sirve. el programa solo lee de ahi `GJ_GameSheet02/03/04`,
`GameSheetGlow`, `LaunchSheet`, `BE_GameSheet01` y `GauntletSheet` -- y
solo para pedir prestadas las *coordenadas* cuando a un pack le falta su
propio plist y las dimensiones del png coinciden exacto.

(el .exe ya trae una de estas referencias empaquetada adentro, asi que si
usas el ejecutable no hace falta que consigas nada de esto a mano.)

## Por que esta herramienta nunca toca `GJ_GameSheet` (sin numero)

esto es lo mas importante de entender antes de usar el programa, por eso
tiene su propia seccion.

Geometry Dash tiene **dos** sheets con nombres que se confunden facil:

- `GJ_GameSheet02` / `03` / `04` / `Glow` -- sprites de **menu, UI e
  iconos**. los texture packs personalizan estos.
- `GJ_GameSheet` (sin numero) -- el sheet **in-game**: pinchos, bloques,
  orbes, portales y decoraciones que aparecen dentro de los niveles.

la gran mayoria de los texture packs -- aunque el nombre sugiera lo
contrario -- **solo repintan menu e iconos** y nunca tocan los sprites
in-game. si un pack no trae su propio `GJ_GameSheet`, eso no es un bug
para arreglar. significa que la instalacion de GD que el jugador ya tiene
sigue dando ese archivo, tal cual lo hacia antes de instalar el pack.

un intento anterior (a mano, antes de que existiera este programa) de
portear un pack se equivoco justo en esto: vio que faltaba `GJ_GameSheet`
y copio uno vanilla de otro lado para "completarlo". esa copia no tenia
garantia de coincidir byte a byte con la version de juego del usuario, y
rompio los pinchos decorativos que venian andando bien con la copia real
del usuario todo este tiempo. la solucion fue dejar de hacer eso, asi de
simple.

`gd_tp_porter.guardrails` aplica esto en codigo (`assert_not_protected`,
probado en `tests/test_porter_integration.py::
test_port_pack_jamas_genera_el_sheet_ingame`), no solo en este parrafo:
nada en este programa puede escribir `GJ_GameSheet.png`,
`GJ_GameSheet-hd.png`, `GJ_GameSheet-uhd.png` (ni sus `.plist`) bajo
ninguna circunstancia, ni aunque la carpeta de `--reference` tenga uno. si
un pack en serio trae su propio `GJ_GameSheet` customizado, el programa lo
deja exactamente como esta -- solo que nunca agrega ni reemplaza uno el
mismo.

## Lo que esta herramienta a proposito NO hace

- **Inventar arte que falte.** si un pack nunca dibujo un sprite para algo
  que agrego 2.2 (pinchos decorativos curvos, variantes de brillo de
  boost/portal, etc), el programa no le inventa una textura. esos
  elementos quedan con el arte vanilla de GD, que es el comportamiento
  correcto -- no un bug.
- **Adivinar coordenadas de plist sin evidencia.** el relleno con
  `--reference` solo dispara cuando el png del pack mide exactamente lo
  mismo que el de referencia. si las medidas difieren aunque sea un poco,
  el programa se niega y te dice por que, en vez de tirarte una UI
  desalineada.
- **Modificar sprites in-game**, por lo de arriba.

## Estructura del proyecto

```
gd_tp_porter/
  plist_utils.py      # parseo/arreglo de plist (Rect, fixs de size)
  icon_split.py        # GameSheet02+Glow -> sheets por icono (la separacion para 2.2)
  sheet_audit.py        # arreglo de sheets de menu/UI (plists rotos o faltantes)
  guardrails.py          # la proteccion del sheet in-game explicada arriba
  extract.py              # extraccion de .zip/.rar con fallback para RAR5
  porter.py                # une todo, genera el PortReport
  __main__.py               # CLI (para consola)
  gui_entry.py               # entrada del .exe (doble click / drag&drop)
  vanilla_reference/          # coordenadas vanilla empaquetadas en el .exe
build_entry.py                  # wrapper que usa pyinstaller para compilar
tests/                            # suite de pytest, incluye el test de regresion del sheet in-game
```

## Compilar el .exe a mano

Los releases en GitHub ya traen el ejecutable compilado (ver el workflow
en `.github/workflows/build-release.yml`, que corre solo al publicar un
release). Si lo querés armar vos:

```bash
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --name gd-tp-porter --onefile --console \
  --add-data "gd_tp_porter/vanilla_reference:gd_tp_porter/vanilla_reference" \
  --collect-all rarfile \
  build_entry.py
```

(en windows el separador de `--add-data` es `;` en vez de `:` -- el
workflow ya tiene los dos casos cubiertos)

## Creditos

La idea de como separar los iconos (que frames van a que sheet de 2.2, y
como armar el atlas resultante) la resolvio originalmente
[2.2tpconvert de Weebifying](https://github.com/Weebifying/2.2tpconvert).
Este proyecto reimplementa esa logica con otra estructura interna (sin
regex para el textureRect, las 3 calidades en una sola pasada) y le suma
el arreglo de plists y las protecciones de mas arriba.

## Licencia

MIT -- ver [LICENSE](LICENSE).
