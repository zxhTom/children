// Run with: node tests/test_edit_ui.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const nodes = new Map();
function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
        value: '', hidden: false, checked: false, files: [], textContent: '',
        reset() {}, scrollIntoView() {}, focus() {}, querySelectorAll() { return []; },
    });
    return nodes.get(id);
}
const document = {
    getElementById: node,
    querySelector: node,
    querySelectorAll() { return []; },
    addEventListener() {},
};
const context = vm.createContext({ document });
vm.runInContext(fs.readFileSync('backend/static/app.js', 'utf8'), context);
vm.runInContext(`
state.children = [{ id: 7, name: '小星', birth_date: '2025-01-01' }];
state.checkups = [{ id: 3, child_id: 7, checkup_date: '2025-03-02T12:00:00',
  hospital: '社区医院', report_text: '记录', weight_kg: 4.2, height_cm: null,
  head_cm: null, next_checkup_date: null, next_checkup_notes: null,
  media_url: '/static_uploads/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg' }];
api = async (url, options) => { globalThis.lastRequest = { url, options }; return {}; };
refresh = async () => {};
toast = () => {};
`, context);

async function main() {
    vm.runInContext("openRecordEdit('checkup', 3)", context);
    assert.equal(node('checkupEditId').value, '3');
    assert.equal(node('checkupDate').value, '2025-03-02');
    assert.equal(node('checkupWeight').value, 4.2);
    assert.equal(node('checkupRemoveMediaWrap').hidden, false);
    await vm.runInContext('saveCheckup()', context);
    let request = context.lastRequest;
    assert.equal(request.url, '/api/checkups/3');
    assert.equal(request.options.method, 'PATCH');
    let payload = JSON.parse(request.options.body);
    assert.equal(payload.weight_kg, 4.2);
    assert.equal(Object.hasOwn(payload, 'media_url'), false);

    vm.runInContext("openRecordEdit('checkup', 3)", context);
    node('checkupRemoveMedia').checked = true;
    await vm.runInContext('saveCheckup()', context);
    request = context.lastRequest;
    payload = JSON.parse(request.options.body);
    assert.equal(payload.media_url, null);
    console.log('edit UI flow passed');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
