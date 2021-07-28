import pytest, json
from collections import Counter
from limeutils import listify

from app import ic
from app.auth import Permission

param = [
    ('app.foo', 'App for Foo', 'App for Foo', 201), ('app.foo', '', 'App Foo', 201),
    ('app.foo.bar', '', 'App Foo Bar', 201), ('', 'Meh', '', 422),
]
@pytest.mark.parametrize('code, name, finalname, status', param)
# @pytest.mark.focus
def test_create_perm(loop, client, auth_headers_tempdb, code, name, finalname, status):
    headers, *_ = auth_headers_tempdb

    d = json.dumps(dict(code=code, name=name))
    res = client.post('/permission', headers=headers, data=d)
    data = res.json()
    
    assert res.status_code == status
    if res.status_code == 201:
        assert data.get('name') == finalname
        assert data.get('code') == code

param = [
    ('foo.read', ['NoaddGroup']),
    (['foo.read'], ['NoaddGroup']),
    ('user.read', ['StaffGroup', 'AdminGroup']),
    (['foo.read', 'foo.update'], ['NoaddGroup']),
    (['foo.read', 'foo.update', 'user.create'], ['StaffGroup', 'AdminGroup', 'NoaddGroup']),
    ([], []), ('', [])
]
@pytest.mark.parametrize('perms, out', param)
# @pytest.mark.focus
def test_permission_get_groups(tempdb, loop, perms, out):
    async def ab():
        await tempdb()
        groups = await Permission.get_groups(*listify(perms))
        assert Counter(groups) == Counter(out)
    loop.run_until_complete(ab())

