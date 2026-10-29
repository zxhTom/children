// Run with: node tests/test_handbook_nav.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const nodes = new Map();
function node(id) {
    if (!nodes.has(id)) nodes.set(id, { value: '', innerHTML: '', focus() {} });
    return nodes.get(id);
}
const context = vm.createContext({ document: { getElementById: node, addEventListener() {} } });
vm.runInContext(fs.readFileSync('backend/static/app.js', 'utf8'), context);
vm.runInContext(`
state.children = [{ id: 3, name: '小星', birth_date: '2024-01-31' }];
state.childId = 3;
state.handbookMonth = 5;
renderHandbook();
`, context);
const html = node('handbookContent').innerHTML;
assert.match(html, /<option value="5" selected>/);
assert.match(html, /data-chapter-month="5"/);
assert.match(html, /data-chapter-step="-1"/);
assert.match(html, /data-chapter-step="1"/);
assert.match(html, /data-chapter-action="entry"/);
assert.match(html, /data-chapter-action="checkup"/);
assert.match(html, /data-chapter-action="growth"/);

vm.runInContext(`
switchTab = () => {};
renderPrompts = () => {};
toast = () => {};
state.handbookMonth = 5;
openChapterForm('entry');
`, context);
assert.equal(node('entryDate').value, '', 'past chapter must require the real event date');
assert.match(node('entryChildren').innerHTML, /value="3" checked/);

vm.runInContext(`openChapterForm('checkup'); openChapterForm('growth');`, context);
assert.equal(node('checkupDate').value, '');
assert.equal(node('growthDate').value, '');
assert.equal(node('checkupChild').value, '3');
assert.equal(node('growthChild').value, '3');

vm.runInContext(`state.handbookMonth = ageMonth('2024-01-31', today()); openChapterForm('entry');`, context);
assert.equal(node('entryDate').value, vm.runInContext('today()', context));
console.log('handbook navigation and draft flow passed');
