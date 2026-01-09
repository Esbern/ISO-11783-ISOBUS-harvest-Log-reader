import json
from pathlib import Path

from pyagri import geo


def make_taskdata(tmp_path, field_id='F1', year='2020'):
    taskdata = f'''<TaskData>
  <PDT A="P1" B="Wheat" />
  <PFD A="{field_id}" C="Field 1">
    <PLN>
      <LSG>
        <PNT C="55.0" D="12.0" />
        <PNT C="55.1" D="12.1" />
        <PNT C="55.0" D="12.0" />
      </LSG>
    </PLN>
  </PFD>
  <TSK A="T1" E="{field_id}">
    <TLG A="log1" />
    <TIM A="{year}-01-01T00:00:00Z" />
    <PAN A="P1" />
  </TSK>
</TaskData>'''
    p = tmp_path / 'TaskData'
    p.mkdir()
    (p / 'TaskData.xml').write_text(taskdata)
    return str(p)


def test_geojson_append(tmp_path):
    out = tmp_path / 'out.geojson'
    # initial file with one feature
    initial = {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'properties': {'TaskID': 'existing'},
                'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [0, 0]]]},
            }
        ],
    }
    out.write_text(json.dumps(initial))

    td = make_taskdata(tmp_path, field_id='F2', year='2021')
    rc = geo.extract_taskdata_to_geojson(td, str(out))
    assert rc == 0

    data = json.loads(out.read_text())
    assert data['type'] == 'FeatureCollection'
    assert len(data['features']) == 2
    ids = [f['properties'].get('TaskID') for f in data['features']]
    assert 'existing' in ids
