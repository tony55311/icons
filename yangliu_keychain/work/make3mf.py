"""Pack N STL parts into one Bambu-style 3MF object: make3mf.py out.3mf name stl:extruder:partname ..."""
import trimesh, zipfile, sys
out, name, specs = sys.argv[1], sys.argv[2], [a.split(':') for a in sys.argv[3:]]
ms = [trimesh.load(p) for p, _, _ in specs]
lo = min(m.bounds[0][0] for m in ms), min(m.bounds[0][1] for m in ms)
hi = max(m.bounds[1][0] for m in ms), max(m.bounds[1][1] for m in ms)
c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
def mesh_xml(m):
    v = '\n'.join(f'<vertex x="{x-c[0]:.4f}" y="{y-c[1]:.4f}" z="{z:.4f}"/>' for x, y, z in m.vertices)
    t = '\n'.join(f'<triangle v1="{a}" v2="{b}" v3="{d}"/>' for a, b, d in m.faces)
    return f'<mesh><vertices>\n{v}\n</vertices><triangles>\n{t}\n</triangles></mesh>'
N = len(ms); oid = N + 1
objs = '\n'.join(f'<object id="{i+1}" type="model">{mesh_xml(m)}</object>' for i, m in enumerate(ms))
comps = ''.join(f'<component objectid="{i+1}"/>' for i in range(N))
model = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">
<metadata name="Application">BambuStudio-01.10.00.00</metadata>
<metadata name="BambuStudio:3mfVersion">1</metadata>
<metadata name="Title">{name}</metadata>
<resources>
{objs}
<object id="{oid}" type="model"><components>{comps}</components></object>
</resources>
<build><item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 128 128 0" printable="1"/></build>
</model>'''
parts = '\n'.join(f'''    <part id="{i+1}" subtype="normal_part">
      <metadata key="name" value="{pn}"/>
      <metadata key="extruder" value="{ex}"/>
    </part>''' for i, (_, ex, pn) in enumerate(specs))
cfg = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="{oid}">
    <metadata key="name" value="{name}"/>
    <metadata key="extruder" value="1"/>
{parts}
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
