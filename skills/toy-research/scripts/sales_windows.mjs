export function aggregateDays(rows, end, days) {
  const byDate=new Map();
  for(const row of rows) {
    if (byDate.has(row.dt)) throw Error(`重复日销量日期 ${row.dt}`);
    byDate.set(row.dt,row.units_sold);
  }
  let total=0,covered=0;
  const date=new Date(`${end}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) throw Error('无效销量截止日期');
  for(let i=0;i<days;i++) {
    const value=byDate.get(date.toISOString().slice(0,10));
    if (Number.isFinite(value) && value>=0) {total+=value;covered++;}
    date.setUTCDate(date.getUTCDate()-1);
  }
  date.setUTCDate(date.getUTCDate()+1);
  return {value:covered===days?total:null,covered_days:covered,days,
    period_start:date.toISOString().slice(0,10),period_end:end,source:'FastMoss salesTrend',
    value_type:'third_party_estimate',scope:'product',timezone:'source_not_specified'};
}

export function mergeHistory(existing, incoming) {
  const incomingDates=new Set();
  for(const row of incoming) {
    if (incomingDates.has(row.dt)) throw Error(`接口返回重复日期 ${row.dt}`);
    incomingDates.add(row.dt);
  }
  return [...new Map([...existing,...incoming].map(row=>[row.dt,row])).values()].sort((a,b)=>a.dt.localeCompare(b.dt));
}
