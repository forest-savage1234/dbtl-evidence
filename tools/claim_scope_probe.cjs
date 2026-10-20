'use strict';
const fs = require('node:fs'), vm = require('node:vm'), crypto = require('node:crypto');
const path = process.argv[2];
if (!path) throw Error('Pass the exact Claim Review index.html snapshot path.');
const raw=fs.readFileSync(path), expected='dc3cf7bb283d2e6eac5043be81325e5d231dd568';
const blob=crypto.createHash('sha1').update(Buffer.from('blob '+raw.length+'\0')).update(raw).digest('hex');
if(blob!==expected) throw Error('Snapshot differs from audited Git blob: '+blob);
const code=raw.toString('utf8'), scripts=[...code.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const core=scripts.find(m=>m[2].includes('return {sha256,decimal,rational'));
if(!core) throw Error('Claim core not found');
const ctx=vm.createContext({TextDecoder,TextEncoder,Uint8Array,DataView,console});
vm.runInContext(scripts[0][2],ctx,{timeout:10000});
vm.runInContext(core[2],ctx,{timeout:10000});
const C=ctx.ClaimCore, enc=new TextEncoder(), out=[];
function run(id,csv,spec,expected,reason){
 const bytes=enc.encode(csv);
 const r=C.review({filename:'probe.csv',sheet:'Table',conditions:[],dp:2,requireConditions:false,...spec},bytes);
 const observations={rounded:r.rounded,numericalStatus:r.numericalStatus,overallStatus:r.overallStatus,
   conditionStatus:r.conditionStatus,error:r.error,replicates:r.replicates,
   arithmeticDetail:r.checks.find(c=>c.name==='Declared arithmetic')?.detail};
 for(const [k,v] of Object.entries(expected)) if(observations[k]!==v) throw Error(id+' unexpected '+k);
 out.push({id,kind:'synthetic scope probe',reason,observed:observations,expectation_met:true});
}
run('CR-01','product_g,biomass_g\n10,20\n',
 {inputs:[{cell:'A2',unit:'g',headerCell:'A1',headerText:'product_g'},
          {cell:'B2',unit:'g',headerCell:'B1',headerText:'biomass_g'}],
 op:'divide',outputUnit:'g/g',reported:'0.5'},
 {rounded:'0.50',numericalStatus:'SOURCE_REPLAY',overallStatus:'PARTIAL_SUPPORT'},
 'Dimensions and headers allow product/biomass. Arithmetic is valid; a substrate-yield estimand is not established.');
run('CR-02','product_g,substrate_g\n1,1\n9,3\n',
 {inputs:[{cells:'A2:A3',unit:'g',replicateType:'biological'},
          {cells:'B2:B3',unit:'g',replicateType:'biological'}],
 op:'divide',outputUnit:'g/g',reported:'2.5'},
 {rounded:'2.50',numericalStatus:'SOURCE_REPLAY',overallStatus:'PARTIAL_SUPPORT'},
 'Ratio of group means is 2.5. Mean of paired ratios is 2.0. The core explicitly warns it uses group means.');
run('CR-03','source_id,product_g_L,physical_origin\nlabel1,1,same-culture\nlabel2,1,same-culture\nlabel3,1,same-culture\n',
 {inputs:[{cells:'B2:B4',unit:'g/L',replicateType:'biological',idCells:'A2:A4',expectedN:'3'}],
 op:'mean',outputUnit:'g/L',reported:'1'},
 {rounded:'1.00',numericalStatus:'SOURCE_REPLAY',overallStatus:'PARTIAL_SUPPORT'},
 'Three labels count as observations but do not establish three independent cultures. The report retains NOT_ESTABLISHED.');
if(out.at(-1).observed.replicates[0].independence!=='NOT_ESTABLISHED')throw Error('Independence warning lost');
run('CR-04','value\n1\n',
 {inputs:[{cell:'A2',unit:'g/L'}],op:'identity',outputUnit:'g/L',expectedHash:'0'.repeat(64)},
 {numericalStatus:'WITHHELD',overallStatus:'REVIEW_REQUIRED'},
 'Positive control: declared source hash mismatch withholds arithmetic support.');
run('CR-05','value\n1\n',
 {inputs:[{cell:'A2',unit:'g'}],op:'identity',outputUnit:'g/L'},
 {numericalStatus:'WITHHELD',overallStatus:'REVIEW_REQUIRED'},
 'Positive control: incompatible dimensions withhold arithmetic support.');
process.stdout.write(JSON.stringify({snapshot_git_blob:blob,sha256:crypto.createHash('sha256').update(raw).digest('hex'),
 runtime:process.version,results:out},null,2)+'\n');
