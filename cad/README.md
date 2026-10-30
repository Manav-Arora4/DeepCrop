# CAD: Field Sensor Unit

A 3D design of the finished field unit for one potted tomato plant:
- the ESP32-S3 and sensor boards in a 3D-printable case on a stake
- the DHT22 inside a radiation shield at canopy height
- the soil-moisture and pH probes in the soil
- cable runs and USB-C power

Everything is generated from [`field_unit.py`](field_unit.py) (build123d). Units are millimetres.

| File | What it is |
|---|---|
| `out/field_unit_assembly.step` | Full assembly in colour, for Fusion 360, FreeCAD or Onshape |
| `out/print/case_body.stl` | Case body, ready to print |
| `out/print/case_lid.stl` | Case lid (print in clear PETG) |
| `out/print/shield.stl` | DHT22 radiation shield |
| `viewer.html` | Interactive 3D viewer page |

## Opening the CAD files in a browser

No CAD software needs to be installed for any of these options.

### 1. Shared 3D viewer link (easiest for showing someone)

The interactive viewer is published as a private claude.ai page. It lets you rotate the model, click parts, see inside the case and open the lid.

To show it to your teacher:
1. Open the page.
2. Click **Share** and give them access.

They can't open the link until you do.

### Quickest: one command

```bash
py cad/open_viewer.py
```

This one command does three things:
1. Starts a local server.
2. Opens the viewer in **Helium**, falling back to your default browser if Helium isn't found.
3. Rebuilds the model first if `field_unit.py` changed and build123d is installed.

Press `Ctrl+C` in the terminal to stop it. If Helium is installed somewhere unusual, set `HELIUM_PATH` to its `chrome.exe`.

### 2. Run the same viewer from this repository (manual steps)

This needs the repo's Python virtual environment (`.venv`) with build123d installed.

Install build123d once:

```bash
.venv/Scripts/python -m pip install build123d
```

Generate the viewer meshes. They are git-ignored, so you need to do this after every fresh clone and after every model change:

```bash
.venv/Scripts/python cad/field_unit.py
```

```bash
.venv/Scripts/python cad/pack_viewer.py
```

Serve the folder:

```bash
.venv/Scripts/python -m http.server 8000 --directory cad
```

Then open **http://localhost:8000/viewer.html** in any browser. Double-clicking `viewer.html` will **not** work, because browsers block it from loading the model file from disk. Stop the server with `Ctrl+C`.

### 3. Printable parts on GitHub

GitHub shows `.stl` files as rotatable 3D models. Click any of these on the repository page:

- [case_body.stl](https://github.com/Manav-Arora4/DeepCrop/blob/main/cad/out/print/case_body.stl)
- [case_lid.stl](https://github.com/Manav-Arora4/DeepCrop/blob/main/cad/out/print/case_lid.stl)
- [shield.stl](https://github.com/Manav-Arora4/DeepCrop/blob/main/cad/out/print/shield.stl)

GitHub can't preview `.step` files, so use option 4 for the full assembly.

### 4. Full assembly (STEP) in an online viewer

- **[3D Viewer](https://3dviewer.net)**: free, no account needed.
  1. Drag `out/field_unit_assembly.step` onto the page. The file is read in your browser, not uploaded to a server.
  2. Use the tree on the left to hide parts or show only some of them.
- **[Onshape](https://www.onshape.com)**: free education account. Choose **Import** and pick the STEP file. Use it when you want to measure parts, take section views or edit the design.
- **[Autodesk Viewer](https://viewer.autodesk.com)**: free Autodesk account. Upload the STEP file, then share a view link.

## Changing the design

All sizes are constants at the top of `field_unit.py`: the case, stake, shield and probe positions. Edit them, then rerun the two commands from option 2 to rebuild every output.

Board sizes are nominal, so measure your own ESP32-S3 and sensor boards before printing. The plant shape is only illustrative.
