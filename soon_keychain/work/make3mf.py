"""Pack v2 base+top STLs into one 2-part 3MF (Bambu Studio: 1 object, part1=filament1, part2=filament2)."""
import trimesh, zipfile, sys
base = trimesh.load(sys.argv[1]); top = trimesh.load(sys.argv[2]); out = sys.argv[3]
c = (base.bounds[0] + base.bounds[1]) / 2
def mesh_xml(m):
    v = '\n'.join(f'<vertex x="{x-c[0]:.4f}" y="{y-c[1]:.4f}" z="{z:.4f}"/>' for x, y, z in m.vertices)
    t = '\n'.join(f'<triangle v1="{a}" v2="{b}" v3="{d}"/>' for a, b, d in m.faces)
    return f'<mesh><vertices>\n{v}\n</vertices><triangles>\n{t}\n</triangles></mesh>'
model = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">
<metadata name="Application">BambuStudio-01.10.00.00</metadata>
<metadata name="BambuStudio:3mfVersion">1</metadata>
<metadata name="Title">SOON keychain v2</metadata>
<resources>
<object id="1" type="model">{mesh_xml(base)}</object>
<object id="2" type="model">{mesh_xml(top)}</object>
<object id="3" type="model"><components><component objectid="1"/><component objectid="2"/></components></object>
</resources>
<build><item objectid="3" transform="1 0 0 0 1 0 0 0 1 128 128 0" printable="1"/></build>
</model>'''
cfg = '''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="3">
    <metadata key="name" value="SOON_keychain_v2"/>
    <metadata key="extruder" value="1"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="base_orange"/>
      <metadata key="extruder" value="1"/>
    </part>
    <part id="2" subtype="normal_part">
      <metadata key="name" value="top_white"/>
      <metadata key="extruder" value="2"/>
    </part>
  </object>
</config>'''
ct = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
<Default Extension="config" ContentType="text/xml"/>
</Types>'''
rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels)
    z.writestr('3D/3dmodel.model', model); z.writestr('Metadata/model_settings.config', cfg)
print('ok', out)
