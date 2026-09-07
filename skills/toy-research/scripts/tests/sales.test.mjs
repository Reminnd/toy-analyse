import test from 'node:test';
import assert from 'node:assert/strict';
import {aggregateDays,mergeHistory} from '../sales_windows.mjs';

test('28 days never become a complete 30-day month',()=>{
  const rows=Array.from({length:28},(_,i)=>({dt:`2026-08-${String(i+3).padStart(2,'0')}`,units_sold:2}));
  assert.equal(aggregateDays(rows,'2026-08-30',7).value,14);
  assert.equal(aggregateDays(rows,'2026-08-30',30).value,null);
  const complete=mergeHistory([{dt:'2026-08-01',units_sold:3},{dt:'2026-08-02',units_sold:3}],rows);
  assert.equal(aggregateDays(complete,'2026-08-30',30).value,62);
});
test('repeated import replaces a date, while duplicate response dates fail',()=>{
  assert.deepEqual(mergeHistory([{dt:'2026-08-01',units_sold:1}],[{dt:'2026-08-01',units_sold:2}]),[{dt:'2026-08-01',units_sold:2}]);
  assert.throws(()=>mergeHistory([],[{dt:'2026-08-01',units_sold:1},{dt:'2026-08-01',units_sold:2}]));
});
