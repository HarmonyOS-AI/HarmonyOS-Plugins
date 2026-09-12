import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

export const digest = (data) => createHash('sha256').update(data).digest('hex');
export async function snapshot(root) {
  const files={};
  async function visit(directory){
    for(const item of (await fs.readdir(directory,{withFileTypes:true})).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0)){
      if(['.git','.plugin','.opencode','node_modules','__pycache__'].includes(item.name))continue;
      const full=path.join(directory,item.name),relative=path.relative(root,full);
      if(item.isSymbolicLink()){const target=await fs.readlink(full);files[relative]={symlink:target,sha256:digest(`symlink:${target}`)};continue;}
      if(item.isDirectory()){await visit(full);continue;}
      const bytes=await fs.readFile(full);files[relative]={sha256:digest(bytes),bytes:bytes.length};
      if(bytes.length<200000&&!bytes.includes(0))files[relative].text=bytes.toString('utf8');
    }
  }
  await visit(root);return files;
}
export function changes(before,after){return [...new Set([...Object.keys(before),...Object.keys(after)])].filter(file=>before[file]?.sha256!==after[file]?.sha256).sort();}
export async function writeJson(file,value){await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,JSON.stringify(value,null,2)+'\n');}
export function transcript(run){
  return run.messages.flatMap(m=>m.parts.filter(p=>['text','tool'].includes(p.type)).map(p=>p.type==='text'?{type:'text',role:m.info.role,text:p.text}:{type:'tool',tool:p.tool,input:p.state?.input,status:p.state?.status,output:p.state?.output,error:p.state?.error}));
}
