// Run with: node tests/test_handbook.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('backend/static/app.js', 'utf8');
const context = vm.createContext({ document: { addEventListener() {} } });
vm.runInContext(source, context);

assert.equal(vm.runInContext("addBirthMonths('2024-01-31', 1)", context), '2024-02-29');
assert.equal(vm.runInContext("addBirthMonths('2024-01-31', 2)", context), '2024-03-31');
assert.equal(vm.runInContext("ageMonth('2024-01-31', '2024-02-28')", context), 0);
assert.equal(vm.runInContext("ageMonth('2024-01-31', '2024-02-29')", context), 1);
assert.equal(vm.runInContext("ageMonth('2024-01-31', '2024-03-30')", context), 1);
assert.equal(vm.runInContext("ageMonth('2024-01-31', '2024-03-31')", context), 2);
assert.equal(vm.runInContext("ageMonth('2024-01-31', '2024-01-30')", context), -1);

vm.runInContext(`
state.entries = [{ id: 1, child_ids: [3, 4], kind: 'milestone', title: '<script>', content: '一起玩', occurred_at: '2024-02-29T12:00:00' }];
state.checkups = [{ id: 2, child_id: 3, checkup_date: '2024-02-29T12:00:00', weight_kg: 4.2 }];
state.growth = [
  { id: 3, child_id: 3, checkup_id: 2, measured_at: '2024-02-29T12:00:00', weight_kg: 4.2 },
  { id: 4, child_id: 3, checkup_id: null, measured_at: '2024-02-28T12:00:00', weight_kg: 4.1 }
];
state.jaundice = [{ id: 5, child_id: 3, record_date: '2024-02-01T12:00:00', value: 8.2 }];
`, context);
const summary = vm.runInContext(`(() => {
  const events = chapterEvents({ id: 3, birth_date: '2024-01-31' });
  return { types: events.map((event) => event.type), months: events.map((event) => event.month), html: handbookEventHtml(events.find((event) => event.type === 'entry')) };
})()`, context);
assert.deepEqual(Array.from(summary.types).sort(), ['checkup', 'entry', 'growth', 'jaundice']);
assert.deepEqual(Array.from(summary.months), [1, 1, 0, 0]);
assert(summary.html.includes('&lt;script&gt;'));
assert(!summary.html.includes('<script>'));
console.log('handbook flow passed');
