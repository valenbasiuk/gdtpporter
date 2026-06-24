# gd-tp-porter

Portea texture packs de Geometry Dash de la 2.1 para que anden
en la 2.2


## download


[página de Releases](../../releases) — `gd-tp-porter-windows.exe`


```bash
git clone https://github.com/<tu-usuario>/gd-tp-porter.git
cd gd-tp-porter
pip install -r requirements.txt

```bash
sudo apt install p7zip-full       # trae 7z, lee RAR5
sudo apt install libarchive-tools # trae bsdtar
```

```bash
# directo desde el archivo descargado:
python -m gd_tp_porter MiPack.rar

# y de paso te genera un .zip listo para compartir:
python -m gd_tp_porter MiPack.rar --zip

# si ya lo tenes extraido:
python -m gd_tp_porter ./MiPackCarpeta -o ./MiPackCarpeta_2.2

```bash
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --name gd-tp-porter --onefile --console \
  --add-data "gd_tp_porter/vanilla_reference:gd_tp_porter/vanilla_reference" \
  --collect-all rarfile \
  build_entry.py
```

esto no crea arte que no exista - this does not create pixels that doesnt exist, just fills the voids with 2.2 textures.

MIT -- ver [LICENSE](LICENSE).
