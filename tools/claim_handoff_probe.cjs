'use strict';
// Run only an explicitly supplied, hash-pinned snapshot; never download or change the checker.
const fs=require('node:fs'), vm=require('node:vm'), crypto=require('node:crypto'), path=require('node:path');
const [snapshot,output]=process.argv.slice(2);
if(!snapshot||!output)throw Error('Pass audited index.html and a new fixture output directory');
const bytes=fs.readFileSync(snapshot), sha=crypto.createHash('sha256').update(bytes).digest('hex');
if(sha!=='89fd6fe7ebb04640abfbe50889e75fc803e21ee8cadafbdd72c7beb67d8fb874')throw Error('Snapshot hash differs');
if(fs.existsSync(output))throw Error('Output directory already exists');
const scripts=[...bytes.toString('utf8').matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const core=scripts.find(m=>m[2].includes('return {sha256,decimal,rational'));
const ctx=vm.createContext({TextDecoder,TextEncoder,Uint8Array,DataView,console});
vm.runInContext(scripts[0][2],ctx,{timeout:10000});vm.runInContext(core[2],ctx,{timeout:10000});
const source=Buffer.from('product_g,biomass_g\n10,20\n','utf8');
const spec={title:'SYNTHETIC product/biomass ratio, not substrate yield',filename:'source.csv',sheet:'Table',
 recordKind:'synthetic',op:'divide',outputUnit:'g/g',dp:2,reported:'0.5',expectedHash:ctx.ClaimCore.sha256(source),
 inputs:[{cell:'A2',unit:'g',headerCell:'A1',headerText:'product_g'},{cell:'B2',unit:'g',headerCell:'B1',headerText:'biomass_g'}],
 requireConditions:false,conditions:[],citation:'SYNTHETIC fixture; not a published measurement',publicationVersion:'synthetic:1',
 measurementGap:'Instrument-to-value chain is not established.',contextGap:'Physical sample identity is not established.',
 versionNote:'SYNTHETIC fixture, not a publication-history review.'};
const report=ctx.ClaimCore.review(spec,source);
if(report.rounded!=='0.50'||report.overallStatus!=='PARTIAL_SUPPORT')throw Error('Producer probe failed');
fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'source.csv'),source);
fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(path.join(output,'provenance.json'),JSON.stringify({kind:'synthetic producer-core execution',
 snapshot_sha256:sha,tool_version:report.toolVersion,node:process.version,
 source_sha256:report.digest,report_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(output,'report.json'))).digest('hex'),
 boundary:'Producer core invoked with the same report payload as export. No browser UI, project import, author authentication or real-study validation tested.'},null,2)+'\n');
process.stdout.write(JSON.stringify({status:'passed',source_sha256:report.digest,upstream_status:report.overallStatus})+'\n');
