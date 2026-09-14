// Exercise the real Worker validator against currencies offered by both ledgers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../assets/current-system');
const worker = fs.readFileSync(path.join(root, 'cloudflare/worker.js'), 'utf8');
const context = vm.createContext({});
vm.runInContext(worker.replace('export default {', 'const workerExport = {'), context);
const currencies = new Set(['KRW', 'JPY']);
for (const variant of ['product', 'runtime']) {
  const ledger = fs.readFileSync(path.join(root, variant, 'shared-ledger.js'), 'utf8');
  const select = ledger.match(/<select name="currency">([\s\S]*?)<\/select>/);
  assert.ok(select, variant + ' must expose a currency selector');
  for (const match of select[1].matchAll(/<option>([A-Z]{3})<\/option>/g)) currencies.add(match[1]);
}
for (const currency of currencies) {
  context.record = { currency, amount: 1234, date: '2026-11-05', category: '餐饮', method: '现金', note: 'test' };
  assert.equal(vm.runInContext('validateExpense(record)', context), 123400, currency);
}
context.record.currency = 'INVALID';
assert.throws(() => vm.runInContext('validateExpense(record)', context), /currency/);
console.log('PASS: Worker accepts all frontend currencies and JPY; invalid currency rejected');
